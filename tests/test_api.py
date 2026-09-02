from itertools import count

import pytest
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

from app.dependencies import AuthenticatedContext
from app.models import (
    AccessAuditEvent,
    AuthSession,
    Company,
    CompanyMembership,
    Conversation,
    Customer,
    Lead,
    Message,
    User,
)
from app.routers.companies import deactivate_membership
from app.services.agent import (
    BASE_SYSTEM_PROMPT,
    AgentServiceError,
    generate_agent_reply,
)
from app.services.auth import (
    create_session_token,
    hash_password,
    hash_session_token,
    session_expiry,
)


identity_counter = count(1)


def create_company(db, name="Acme", slug="acme"):
    company = Company(name=name, slug=slug)
    db.add(company)
    db.commit()
    return company


def create_identity(db, memberships, email=None):
    user = User(
        email_normalized=email or f"user-{next(identity_counter)}@example.com",
        password_hash=hash_password("correct horse battery staple"),
        is_active=True,
    )
    db.add(user)
    db.flush()
    for company, role in memberships:
        db.add(
            CompanyMembership(
                user_id=user.id,
                company_id=company.id,
                role=role,
                is_active=True,
            )
        )

    token = create_session_token()
    db.add(
        AuthSession(
            user_id=user.id,
            token_hash=hash_session_token(token),
            expires_at=session_expiry(24),
        )
    )
    db.commit()
    return user, token


def tenant_headers(company, token):
    return {
        "Authorization": f"Bearer {token}",
        "X-Company-ID": str(company.id),
    }


def create_lead(client, company, headers, name="Maria"):
    response = client.post(
        "/leads",
        headers=headers,
        json={
            "company_id": company.id,
            "name": name,
            "phone": "11999999999",
            "source": "site",
            "interest": "automacao",
        },
    )
    assert response.status_code == 200
    return response.json()


def create_customer(client, company, headers, name="Joao"):
    response = client.post(
        "/customers",
        headers=headers,
        json={
            "company_id": company.id,
            "name": name,
            "phone": "11888888888",
            "email": "joao@example.com",
        },
    )
    assert response.status_code == 200
    return response.json()


def create_conversation(
    client,
    company,
    headers,
    *,
    lead_id=None,
    customer_id=None,
):
    response = client.post(
        "/conversations",
        headers=headers,
        json={
            "company_id": company.id,
            "channel": "whatsapp",
            "lead_id": lead_id,
            "customer_id": customer_id,
        },
    )
    assert response.status_code == 200
    return response.json()


def test_get_root_remains_public(client):
    response = client.get("/")

    assert response.status_code == 200
    assert response.json() == {
        "name": "Fenato Business Automation API",
        "status": "running",
    }


@pytest.mark.parametrize(
    ("method", "path", "json"),
    [
        ("get", "/companies", None),
        ("get", "/leads", None),
        ("get", "/customers", None),
        ("post", "/conversations", {"company_id": 1, "channel": "web"}),
    ],
)
def test_business_endpoints_require_authentication(client, method, path, json):
    response = client.request(method, path, json=json)

    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "Bearer"


def test_tenant_endpoints_require_company_header(client, db):
    company = create_company(db)
    _, token = create_identity(db, [(company, "member")])

    response = client.get(
        "/leads",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 400
    assert response.json() == {"detail": "X-Company-ID header is required"}


def test_companies_list_only_active_memberships_and_creation_is_blocked(client, db):
    company = create_company(db, name="Company 1", slug="company-1")
    other_company = create_company(db, name="Company 2", slug="company-2")
    hidden_company = create_company(db, name="Hidden", slug="hidden")
    user, token = create_identity(
        db,
        [(company, "owner"), (other_company, "member")],
    )
    inactive_membership = CompanyMembership(
        user_id=user.id,
        company_id=hidden_company.id,
        role="member",
        is_active=False,
    )
    db.add(inactive_membership)
    db.commit()

    response = client.get(
        "/companies",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    assert [item["id"] for item in response.json()] == [company.id, other_company.id]

    create_response = client.post(
        "/companies",
        headers={"Authorization": f"Bearer {token}"},
        json={"name": "Public", "slug": "public"},
    )
    assert create_response.status_code == 403
    assert db.scalar(select(func.count()).select_from(Company)) == 3


def test_membership_administration_is_owner_only_and_tenant_scoped(client, db):
    company = create_company(db, name="Company 1", slug="company-1")
    other_company = create_company(db, name="Company 2", slug="company-2")
    owner, owner_token = create_identity(db, [(company, "owner")])
    _, admin_token = create_identity(db, [(company, "admin")])
    member, member_token = create_identity(db, [(company, "member")])
    other_member, _ = create_identity(db, [(other_company, "member")])
    db.add(
        CompanyMembership(
            user_id=owner.id,
            company_id=other_company.id,
            role="owner",
            is_active=True,
        )
    )
    inactive_user = User(
        email_normalized="inactive-membership@example.com",
        password_hash=hash_password("correct horse battery staple"),
        is_active=True,
    )
    db.add(inactive_user)
    db.flush()
    db.add(
        CompanyMembership(
            user_id=inactive_user.id,
            company_id=company.id,
            role="member",
            is_active=False,
        )
    )
    db.commit()
    owner_headers = tenant_headers(company, owner_token)

    assert client.get(
        f"/companies/{company.id}/memberships",
        headers={"Authorization": f"Bearer {owner_token}"},
    ).status_code == 400
    assert client.get(
        f"/companies/{company.id}/memberships",
        headers=tenant_headers(company, admin_token),
    ).status_code == 403
    assert client.get(
        f"/companies/{company.id}/memberships",
        headers=tenant_headers(company, member_token),
    ).status_code == 403

    memberships_response = client.get(
        f"/companies/{company.id}/memberships",
        headers=owner_headers,
    )
    assert memberships_response.status_code == 200
    memberships = memberships_response.json()
    assert [item["id"] for item in memberships] == sorted(item["id"] for item in memberships)
    assert {item["id"] for item in memberships} == {
        item.id for item in db.scalars(
            select(CompanyMembership).where(CompanyMembership.company_id == company.id)
        )
    }
    assert all("password_hash" not in item for item in memberships)
    assert any(item["is_active"] is False for item in memberships)
    assert all(item["user_id"] != other_member.id for item in memberships)

    other_membership = db.scalar(
        select(CompanyMembership).where(CompanyMembership.user_id == other_member.id)
    )
    cross_tenant_response = client.post(
        f"/companies/{company.id}/memberships/{other_membership.id}/deactivate",
        headers=owner_headers,
    )
    assert cross_tenant_response.status_code == 404
    assert db.get(CompanyMembership, other_membership.id).is_active is True
    assert db.scalar(select(func.count()).select_from(AccessAuditEvent)) == 0

    member_membership = db.scalar(
        select(CompanyMembership).where(CompanyMembership.user_id == member.id)
    )
    assert client.get(
        f"/companies/{other_company.id}/memberships",
        headers=owner_headers,
    ).status_code == 404
    assert member_membership is not None


def test_membership_role_changes_are_audited_and_preserve_an_active_owner(client, db):
    company = create_company(db)
    owner, owner_token = create_identity(db, [(company, "owner")])
    member, _ = create_identity(db, [(company, "member")])
    second_owner, second_owner_token = create_identity(db, [(company, "owner")])
    headers = tenant_headers(company, owner_token)
    owner_membership = db.scalar(
        select(CompanyMembership).where(CompanyMembership.user_id == owner.id)
    )
    member_membership = db.scalar(
        select(CompanyMembership).where(CompanyMembership.user_id == member.id)
    )
    second_owner_membership = db.scalar(
        select(CompanyMembership).where(CompanyMembership.user_id == second_owner.id)
    )

    invalid_response = client.patch(
        f"/companies/{company.id}/memberships/{member_membership.id}/role",
        headers=headers,
        json={"role": "invalid"},
    )
    assert invalid_response.status_code == 422

    update_response = client.patch(
        f"/companies/{company.id}/memberships/{member_membership.id}/role",
        headers=headers,
        json={"role": "admin"},
    )
    assert update_response.status_code == 200
    assert update_response.json()["role"] == "admin"
    event = db.scalar(select(AccessAuditEvent))
    assert (event.actor_user_id, event.target_membership_id, event.action) == (
        owner.id,
        member_membership.id,
        "membership_role_changed",
    )
    assert (event.old_role, event.new_role) == ("member", "admin")
    same_role_response = client.patch(
        f"/companies/{company.id}/memberships/{member_membership.id}/role",
        headers=headers,
        json={"role": "admin"},
    )
    assert same_role_response.status_code == 200
    assert db.scalar(select(func.count()).select_from(AccessAuditEvent)) == 1

    assert client.patch(
        f"/companies/{company.id}/memberships/{owner_membership.id}/role",
        headers=headers,
        json={"role": "admin"},
    ).status_code == 200
    blocked_response = client.post(
        f"/companies/{company.id}/memberships/{second_owner_membership.id}/deactivate",
        headers=tenant_headers(company, second_owner_token),
    )
    assert blocked_response.status_code == 409
    assert db.get(CompanyMembership, second_owner_membership.id).is_active is True
    assert db.scalar(select(func.count()).select_from(AccessAuditEvent)) == 2


def test_membership_deactivation_and_reactivation_are_audited_and_immediate(client, db):
    company = create_company(db)
    _, owner_token = create_identity(db, [(company, "owner")])
    member, member_token = create_identity(db, [(company, "member")])
    headers = tenant_headers(company, owner_token)
    member_headers = tenant_headers(company, member_token)
    membership = db.scalar(
        select(CompanyMembership).where(CompanyMembership.user_id == member.id)
    )

    deactivated = client.post(
        f"/companies/{company.id}/memberships/{membership.id}/deactivate",
        headers=headers,
    )
    assert deactivated.status_code == 200
    assert deactivated.json()["is_active"] is False
    assert client.get("/leads", headers=member_headers).status_code == 404
    assert client.post(
        f"/companies/{company.id}/memberships/{membership.id}/deactivate",
        headers=headers,
    ).status_code == 409

    reactivated = client.post(
        f"/companies/{company.id}/memberships/{membership.id}/reactivate",
        headers=headers,
    )
    assert reactivated.status_code == 200
    assert reactivated.json()["is_active"] is True
    assert client.get("/leads", headers=member_headers).status_code == 200
    assert client.post(
        f"/companies/{company.id}/memberships/{membership.id}/reactivate",
        headers=headers,
    ).status_code == 409
    events = db.scalars(select(AccessAuditEvent).order_by(AccessAuditEvent.id)).all()
    assert [(event.action, event.old_is_active, event.new_is_active) for event in events] == [
        ("membership_deactivated", True, False),
        ("membership_reactivated", False, True),
    ]


def test_inactive_owner_does_not_count_toward_last_active_owner(client, db):
    company = create_company(db)
    active_owner, active_owner_token = create_identity(db, [(company, "owner")])
    inactive_owner = User(
        email_normalized="inactive-owner@example.com",
        password_hash=hash_password("correct horse battery staple"),
        is_active=True,
    )
    db.add(inactive_owner)
    db.flush()
    db.add(
        CompanyMembership(
            user_id=inactive_owner.id,
            company_id=company.id,
            role="owner",
            is_active=False,
        )
    )
    db.commit()
    active_membership = db.scalar(
        select(CompanyMembership).where(CompanyMembership.user_id == active_owner.id)
    )

    response = client.post(
        f"/companies/{company.id}/memberships/{active_membership.id}/deactivate",
        headers=tenant_headers(company, active_owner_token),
    )

    assert response.status_code == 409
    assert db.get(CompanyMembership, active_membership.id).is_active is True
    assert db.scalar(select(func.count()).select_from(AccessAuditEvent)) == 0


def test_audit_persistence_failure_rolls_back_membership_change(db, monkeypatch):
    company = create_company(db)
    owner, _ = create_identity(db, [(company, "owner")])
    member, _ = create_identity(db, [(company, "member")])
    owner_membership = db.scalar(
        select(CompanyMembership).where(CompanyMembership.user_id == owner.id)
    )
    member_membership = db.scalar(
        select(CompanyMembership).where(CompanyMembership.user_id == member.id)
    )
    context = AuthenticatedContext(
        user=owner,
        session=None,  # type: ignore[arg-type]
        company=company,
        membership=owner_membership,
    )
    add = db.add

    def add_invalid_audit_event(instance):
        if isinstance(instance, AccessAuditEvent):
            instance.action = "invalid"
        add(instance)

    monkeypatch.setattr(db, "add", add_invalid_audit_event)

    with pytest.raises(IntegrityError):
        deactivate_membership(db, context, company.id, member_membership.id)

    assert db.get(CompanyMembership, member_membership.id).is_active is True
    assert db.scalar(select(func.count()).select_from(AccessAuditEvent)) == 0


def test_access_audit_event_enforces_known_actions_and_roles(db):
    company = create_company(db)
    actor, _ = create_identity(db, [(company, "owner")])
    membership = db.scalar(
        select(CompanyMembership).where(CompanyMembership.user_id == actor.id)
    )

    db.add(
        AccessAuditEvent(
            company_id=company.id,
            actor_user_id=actor.id,
            target_membership_id=membership.id,
            action="invalid",
        )
    )
    with pytest.raises(IntegrityError):
        db.flush()
    db.rollback()

    db.add(
        AccessAuditEvent(
            company_id=company.id,
            actor_user_id=actor.id,
            target_membership_id=membership.id,
            action="membership_role_changed",
            old_role="invalid",
        )
    )
    with pytest.raises(IntegrityError):
        db.flush()


def test_agent_config_requires_admin_role_and_matching_tenant(client, db):
    company = create_company(db, name="Company 1", slug="company-1")
    other_company = create_company(db, name="Company 2", slug="company-2")
    _, admin_token = create_identity(db, [(company, "admin")])
    _, member_token = create_identity(db, [(company, "member")])
    admin_headers = tenant_headers(company, admin_token)
    member_headers = tenant_headers(company, member_token)

    default_response = client.get(
        f"/companies/{company.id}/agent-config",
        headers=admin_headers,
    )
    assert default_response.status_code == 200
    assert default_response.json()["effective_model"] == "qwen3:8b"

    forbidden_response = client.put(
        f"/companies/{company.id}/agent-config",
        headers=member_headers,
        json={"instructions": "Forbidden", "model": None},
    )
    assert forbidden_response.status_code == 403

    mismatch_response = client.get(
        f"/companies/{other_company.id}/agent-config",
        headers=admin_headers,
    )
    assert mismatch_response.status_code == 404

    update_response = client.put(
        f"/companies/{company.id}/agent-config",
        headers=admin_headers,
        json={
            "instructions": "  Priorize agendamentos.  ",
            "model": "  custom-model  ",
        },
    )
    assert update_response.status_code == 200
    assert update_response.json() == {
        "company_id": company.id,
        "instructions": "Priorize agendamentos.",
        "model": "custom-model",
        "effective_model": "custom-model",
    }


def test_leads_are_scoped_and_body_company_cannot_select_tenant(client, db):
    company = create_company(db, name="Company 1", slug="company-1")
    other_company = create_company(db, name="Company 2", slug="company-2")
    _, token = create_identity(db, [(company, "member")])
    _, other_token = create_identity(db, [(other_company, "member")])
    headers = tenant_headers(company, token)
    other_headers = tenant_headers(other_company, other_token)
    lead = create_lead(client, company, headers)
    other_lead = create_lead(client, other_company, other_headers, name="Ana")

    assert client.get(f"/leads/{lead['id']}", headers=headers).status_code == 200
    assert client.get(f"/leads/{other_lead['id']}", headers=headers).status_code == 404

    list_response = client.get("/leads", headers=headers)
    assert [item["id"] for item in list_response.json()] == [lead["id"]]

    path_list_response = client.get(
        f"/companies/{company.id}/leads",
        headers=headers,
    )
    assert [item["id"] for item in path_list_response.json()] == [lead["id"]]

    mismatch_response = client.post(
        "/leads",
        headers=headers,
        json={
            "company_id": other_company.id,
            "name": "Injected",
            "phone": "11000000000",
            "source": "test",
        },
    )
    assert mismatch_response.status_code == 400
    assert db.scalar(
        select(func.count()).select_from(Lead).where(Lead.name == "Injected")
    ) == 0


def test_one_user_can_switch_memberships_without_mixing_tenant_data(client, db):
    company = create_company(db, name="Company 1", slug="company-1")
    other_company = create_company(db, name="Company 2", slug="company-2")
    _, token = create_identity(
        db,
        [(company, "member"), (other_company, "member")],
    )
    headers = tenant_headers(company, token)
    other_headers = tenant_headers(other_company, token)
    lead = create_lead(client, company, headers, name="Company 1 lead")
    other_lead = create_lead(
        client,
        other_company,
        other_headers,
        name="Company 2 lead",
    )

    assert [item["id"] for item in client.get("/leads", headers=headers).json()] == [
        lead["id"]
    ]
    assert [
        item["id"] for item in client.get("/leads", headers=other_headers).json()
    ] == [other_lead["id"]]


def test_customers_and_lead_conversion_are_tenant_scoped(client, db):
    company = create_company(db, name="Company 1", slug="company-1")
    other_company = create_company(db, name="Company 2", slug="company-2")
    _, token = create_identity(db, [(company, "member")])
    _, other_token = create_identity(db, [(other_company, "member")])
    headers = tenant_headers(company, token)
    other_headers = tenant_headers(other_company, other_token)
    customer = create_customer(client, company, headers)
    other_customer = create_customer(client, other_company, other_headers, name="Ana")
    lead = create_lead(client, company, headers)
    other_lead = create_lead(client, other_company, other_headers, name="Other lead")

    assert (
        client.get(f"/customers/{customer['id']}", headers=headers).status_code == 200
    )
    assert (
        client.get(f"/customers/{other_customer['id']}", headers=headers).status_code
        == 404
    )
    assert client.get("/customers", headers=headers).json()[0]["id"] == customer["id"]

    convert_response = client.post(f"/leads/{lead['id']}/convert", headers=headers)
    assert convert_response.status_code == 200
    assert convert_response.json()["company_id"] == company.id

    cross_tenant_response = client.post(
        f"/leads/{other_lead['id']}/convert",
        headers=headers,
    )
    assert cross_tenant_response.status_code == 404
    db.refresh(db.get(Lead, other_lead["id"]))
    assert db.get(Lead, other_lead["id"]).status == "new"


def test_conversation_rules_and_tenant_ownership(client, db):
    company = create_company(db, name="Company 1", slug="company-1")
    other_company = create_company(db, name="Company 2", slug="company-2")
    _, token = create_identity(db, [(company, "member")])
    _, other_token = create_identity(db, [(other_company, "member")])
    headers = tenant_headers(company, token)
    other_headers = tenant_headers(other_company, other_token)
    lead = create_lead(client, company, headers)
    customer = create_customer(client, company, headers)
    other_lead = create_lead(client, other_company, other_headers, name="Ana")

    missing_owner = client.post(
        "/conversations",
        headers=headers,
        json={"company_id": company.id, "channel": "web"},
    )
    assert missing_owner.status_code == 400

    both_owners = client.post(
        "/conversations",
        headers=headers,
        json={
            "company_id": company.id,
            "channel": "web",
            "lead_id": lead["id"],
            "customer_id": customer["id"],
        },
    )
    assert both_owners.status_code == 400

    cross_owner = client.post(
        "/conversations",
        headers=headers,
        json={
            "company_id": company.id,
            "channel": "web",
            "lead_id": other_lead["id"],
        },
    )
    assert cross_owner.status_code == 404

    conversation = create_conversation(
        client,
        company,
        headers,
        lead_id=lead["id"],
    )
    assert (
        client.get(
            f"/conversations/{conversation['id']}",
            headers=other_headers,
        ).status_code
        == 404
    )
    assert client.get("/companies/999/conversations", headers=headers).status_code == 404


def test_conversation_owner_database_constraint(db):
    company = create_company(db)
    lead = Lead(
        company_id=company.id,
        name="Maria",
        phone="11999999999",
        source="site",
    )
    customer = Customer(
        company_id=company.id,
        name="Joao",
        phone="11888888888",
    )
    db.add_all([lead, customer])
    db.commit()

    for lead_id, customer_id in ((None, None), (lead.id, customer.id)):
        db.add(
            Conversation(
                company_id=company.id,
                lead_id=lead_id,
                customer_id=customer_id,
                channel="whatsapp",
            )
        )
        with pytest.raises(IntegrityError):
            db.flush()
        db.rollback()


def test_message_sender_cannot_be_forged_and_cross_tenant_has_no_effect(client, db):
    company = create_company(db, name="Company 1", slug="company-1")
    other_company = create_company(db, name="Company 2", slug="company-2")
    _, token = create_identity(db, [(company, "member")])
    _, other_token = create_identity(db, [(other_company, "member")])
    headers = tenant_headers(company, token)
    other_headers = tenant_headers(other_company, other_token)
    other_lead = create_lead(client, other_company, other_headers)
    other_conversation = create_conversation(
        client,
        other_company,
        other_headers,
        lead_id=other_lead["id"],
    )

    cross_response = client.post(
        f"/conversations/{other_conversation['id']}/messages",
        headers=headers,
        json={"sender_type": "human", "content": "Cross tenant"},
    )
    assert cross_response.status_code == 404

    forged_response = client.post(
        f"/conversations/{other_conversation['id']}/messages",
        headers=other_headers,
        json={"sender_type": "system", "content": "Forged"},
    )
    assert forged_response.status_code == 403

    valid_response = client.post(
        f"/conversations/{other_conversation['id']}/messages",
        headers=other_headers,
        json={"sender_type": "human", "content": "Valid"},
    )
    assert valid_response.status_code == 200
    assert db.scalar(select(func.count()).select_from(Message)) == 1


def test_remaining_cross_tenant_operations_fail_without_mutation(client, db):
    company = create_company(db, name="Company 1", slug="company-1")
    other_company = create_company(db, name="Company 2", slug="company-2")
    _, token = create_identity(db, [(company, "member")])
    _, other_token = create_identity(db, [(other_company, "member")])
    headers = tenant_headers(company, token)
    other_headers = tenant_headers(other_company, other_token)
    other_lead = create_lead(client, other_company, other_headers)
    other_customer = create_customer(client, other_company, other_headers)
    other_conversation = create_conversation(
        client,
        other_company,
        other_headers,
        customer_id=other_customer["id"],
    )

    update_response = client.patch(
        f"/leads/{other_lead['id']}",
        headers=headers,
        json={"status": "won"},
    )
    assert update_response.status_code == 404

    customer_response = client.post(
        "/customers",
        headers=headers,
        json={
            "company_id": other_company.id,
            "name": "Injected customer",
            "phone": "11000000000",
        },
    )
    assert customer_response.status_code == 400

    conversation_response = client.post(
        "/conversations",
        headers=headers,
        json={
            "company_id": other_company.id,
            "channel": "web",
            "lead_id": other_lead["id"],
        },
    )
    assert conversation_response.status_code == 400

    for path in (
        f"/companies/{other_company.id}/leads",
        f"/companies/{other_company.id}/customers",
        f"/companies/{other_company.id}/conversations",
        f"/conversations/{other_conversation['id']}/messages",
    ):
        assert client.get(path, headers=headers).status_code == 404

    db.refresh(db.get(Lead, other_lead["id"]))
    assert db.get(Lead, other_lead["id"]).status == "new"
    assert db.scalar(
        select(func.count())
        .select_from(Customer)
        .where(Customer.name == "Injected customer")
    ) == 0


def test_agent_reply_persists_messages_with_company_configuration(
    client,
    db,
    monkeypatch,
):
    company = create_company(db)
    _, token = create_identity(db, [(company, "owner")])
    headers = tenant_headers(company, token)
    config_response = client.put(
        f"/companies/{company.id}/agent-config",
        headers=headers,
        json={"instructions": "Priorize agendamentos.", "model": "company-model"},
    )
    assert config_response.status_code == 200
    lead = create_lead(client, company, headers)
    conversation = create_conversation(
        client,
        company,
        headers,
        lead_id=lead["id"],
    )

    def fake_generate_agent_reply(message, history, instructions=None, model=None):
        assert message == "Ola"
        assert history == []
        assert instructions == "Priorize agendamentos."
        assert model == "company-model"
        return "Resposta do agente"

    monkeypatch.setattr(
        "app.routers.conversations.generate_agent_reply",
        fake_generate_agent_reply,
    )

    response = client.post(
        f"/conversations/{conversation['id']}/agent-reply",
        headers=headers,
        json={"content": "Ola"},
    )
    assert response.status_code == 200

    messages = client.get(
        f"/conversations/{conversation['id']}/messages",
        headers=headers,
    ).json()
    assert [(item["sender_type"], item["content"]) for item in messages] == [
        ("customer", "Ola"),
        ("agent", "Resposta do agente"),
    ]


def test_cross_tenant_agent_reply_does_not_call_agent_or_persist(client, db, monkeypatch):
    company = create_company(db, name="Company 1", slug="company-1")
    other_company = create_company(db, name="Company 2", slug="company-2")
    _, token = create_identity(db, [(company, "member")])
    _, other_token = create_identity(db, [(other_company, "member")])
    headers = tenant_headers(company, token)
    other_headers = tenant_headers(other_company, other_token)
    other_lead = create_lead(client, other_company, other_headers)
    other_conversation = create_conversation(
        client,
        other_company,
        other_headers,
        lead_id=other_lead["id"],
    )

    def must_not_run(*args, **kwargs):
        raise AssertionError("agent service must not be called")

    monkeypatch.setattr(
        "app.routers.conversations.generate_agent_reply",
        must_not_run,
    )
    response = client.post(
        f"/conversations/{other_conversation['id']}/agent-reply",
        headers=headers,
        json={"content": "Ola"},
    )

    assert response.status_code == 404
    assert db.scalar(select(func.count()).select_from(Message)) == 0


def test_agent_reply_failure_preserves_customer_message_without_internal_details(
    client,
    db,
    monkeypatch,
):
    company = create_company(db)
    _, token = create_identity(db, [(company, "member")])
    headers = tenant_headers(company, token)
    lead = create_lead(client, company, headers)
    conversation = create_conversation(
        client,
        company,
        headers,
        lead_id=lead["id"],
    )

    def fake_generate_agent_reply(*args, **kwargs):
        raise AgentServiceError(
            "Connection refused http://localhost:11434/api/chat qwen3:8b"
        )

    monkeypatch.setattr(
        "app.routers.conversations.generate_agent_reply",
        fake_generate_agent_reply,
    )
    response = client.post(
        f"/conversations/{conversation['id']}/agent-reply",
        headers=headers,
        json={"content": "Ola"},
    )

    assert response.status_code == 503
    assert response.json() == {"detail": "Agent service unavailable"}
    assert "Connection refused" not in response.text
    messages = client.get(
        f"/conversations/{conversation['id']}/messages",
        headers=headers,
    ).json()
    assert [(item["sender_type"], item["content"]) for item in messages] == [
        ("customer", "Ola")
    ]


def test_agent_service_uses_company_overrides(monkeypatch):
    captured = {}

    class FakeResponse:
        def raise_for_status(self):
            pass

        def json(self):
            return {"message": {"content": "Resposta"}}

    def fake_post(url, json, timeout):
        captured["url"] = url
        captured["json"] = json
        captured["timeout"] = timeout
        return FakeResponse()

    monkeypatch.setattr("app.services.agent.httpx.post", fake_post)
    response = generate_agent_reply(
        message="Olá",
        history=[],
        instructions="Priorize agendamentos.",
        model="company-model",
    )

    assert response == "Resposta"
    assert captured["url"] == "http://localhost:11434/api/chat"
    assert captured["json"]["model"] == "company-model"
    assert captured["json"]["messages"][0]["content"] == (
        f"{BASE_SYSTEM_PROMPT}\n\nInstruções da empresa:\nPriorize agendamentos."
    )
