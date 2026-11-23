def add_record_comment(organization, module, object_id, body, user=None):
    from comments.models import RecordComment

    text = (body or "").strip()
    if organization is None or not module or object_id in (None, "") or not text:
        return None
    author = user if getattr(user, "is_authenticated", False) else None
    comment = RecordComment.objects.create(
        organization=organization,
        module=module[:64],
        object_id=str(object_id)[:64],
        body=text,
        author=author,
        created_by=author,
    )
    _notify_watchers(comment)
    return comment


def _notify_watchers(comment):
    from dms.models import WorkflowCase
    from notifications.services import push_inbox

    case = (
        WorkflowCase.objects.filter(
            organization=comment.organization,
            module=comment.module,
            object_id=comment.object_id,
        )
        .select_related("last_actor")
        .first()
    )
    if case is None or case.last_actor_id is None or case.last_actor_id == comment.author_id:
        return
    push_inbox(
        comment.organization,
        [case.last_actor],
        title=f"Comment on {comment.module} #{comment.object_id}",
        body=comment.body[:500],
        href=f"/comments?module={comment.module}&object={comment.object_id}",
        module=comment.module,
        object_id=comment.object_id,
        kind="comment",
    )
