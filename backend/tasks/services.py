def assign_task(organization, title, body="", role_code="", module="", object_id="", user=None):
    from accounts.models import Role
    from notifications.services import push_inbox, record_href
    from tasks.models import WorkTask

    label = (title or "Task").strip()
    if organization is None or not label:
        return None
    code = (role_code or "").strip()
    role = Role.objects.filter(organization=organization, code=code).first() if code else None
    actor = user if getattr(user, "is_authenticated", False) else None
    task = WorkTask.objects.create(
        organization=organization,
        title=label[:180],
        body=body or "",
        role=role,
        role_code=code[:64],
        module=(module or "")[:64],
        object_id=str(object_id or "")[:64],
        created_by=actor,
    )
    from accounts.models import UserProfile, UserRole

    users = []
    if role is not None:
        users.extend(link.user for link in UserRole.objects.filter(role=role).select_related("user"))
    if code:
        users.extend(
            profile.user
            for profile in UserProfile.objects.filter(organization=organization, role=code).select_related("user")
        )
    if users:
        push_inbox(
            organization,
            users,
            title=label,
            body=body or "A workflow assigned this task.",
            href=record_href(module, object_id) if module else "/tasks",
            module=module,
            object_id=object_id,
            kind="task",
        )
    return task
