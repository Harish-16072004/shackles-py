"""Email template rendering using in-memory Jinja2 templates.

Templates are Python string constants loaded into a DictLoader. This
keeps the deployment simple — no external template directory needed.
"""

from jinja2 import DictLoader, Environment, select_autoescape


# ============================================================
# Base layout — every email extends this
# ============================================================

_BASE = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{{ subject }}</title>
</head>
<body style="margin:0;padding:0;background:#f9fafb;font-family:'Segoe UI',Arial,sans-serif;color:#333;">
  <table width="100%" cellpadding="0" cellspacing="0" style="padding:32px 0;">
    <tr><td align="center">
      <table width="540" cellpadding="0" cellspacing="0" style="background:#ffffff;border-radius:12px;border:1px solid #e5e7eb;overflow:hidden;">
        <tr>
          <td style="background:#111827;color:#ffffff;padding:20px 32px;">
            <h1 style="margin:0;font-size:18px;letter-spacing:0.5px;">Shackles Symposium</h1>
          </td>
        </tr>
        <tr>
          <td style="padding:32px;">
            {% block content %}{% endblock %}
          </td>
        </tr>
        <tr>
          <td style="padding:16px 32px;background:#f9fafb;border-top:1px solid #e5e7eb;text-align:center;">
            <p style="margin:0;font-size:12px;color:#6b7280;">
              Automated message from Shackles Symposium {{ year }}.
            </p>
          </td>
        </tr>
      </table>
    </td></tr>
  </table>
</body>
</html>
"""


# ============================================================
# Specific templates
# ============================================================

_PAYMENT_VERIFIED = """{% extends "base" %}
{% block content %}
<p style="margin:0 0 16px;font-size:16px;">Hi <strong>{{ user_name }}</strong>,</p>
<p style="margin:0 0 20px;font-size:15px;color:#555;line-height:1.6;">
  Your payment for Shackles Symposium {{ year }} has been verified.
  Your account is now active.
</p>

<div style="margin:20px 0;padding:20px;background:#f3f4f6;border-radius:8px;text-align:center;">
  <p style="margin:0 0 6px;font-size:12px;color:#6b7280;text-transform:uppercase;letter-spacing:0.5px;">Your Shackles ID</p>
  <p style="margin:0;font-size:28px;font-weight:700;font-family:monospace;letter-spacing:2px;color:#111827;">{{ shackles_id }}</p>
</div>

<p style="margin:16px 0;font-size:14px;color:#555;">
  Package: <strong>{{ package_type }}</strong>
</p>

{% if qr_image_url %}
<div style="margin:24px 0;text-align:center;">
  <p style="margin:0 0 8px;font-size:13px;color:#555;">Your QR code is ready</p>
  <img src="{{ qr_image_url }}" alt="QR Code" width="200" height="200" style="border:1px solid #e5e7eb;border-radius:8px;">
  <p style="margin:8px 0 0;font-size:12px;color:#9ca3af;">Show this at all stations.</p>
</div>
{% else %}
<p style="margin:16px 0;font-size:14px;color:#555;">
  Your QR code is available on your dashboard. You'll need it at all
  stations for kit collection, attendance, and event access.
</p>
{% endif %}

<p style="margin-top:24px;font-size:13px;color:#6b7280;">
  Visit your dashboard to view event registrations and download your QR code.
</p>
{% endblock %}
"""


_TEAM_CREATED = """{% extends "base" %}
{% block content %}
<p style="margin:0 0 16px;font-size:16px;">Hi <strong>{{ leader_name }}</strong>,</p>
<p style="margin:0 0 20px;font-size:15px;color:#555;line-height:1.6;">
  Your team <strong>{{ team_name }}</strong> for <strong>{{ event_name }}</strong>
  has been created. You are the team leader.
</p>

<div style="margin:20px 0;padding:20px;background:#fef3c7;border:1px solid #fde68a;border-radius:8px;text-align:center;">
  <p style="margin:0 0 6px;font-size:12px;color:#92400e;text-transform:uppercase;letter-spacing:0.5px;">Join Code — share with teammates</p>
  <p style="margin:0;font-size:28px;font-weight:800;font-family:monospace;letter-spacing:6px;color:#92400e;">{{ join_code }}</p>
</div>

<p style="margin:16px 0;font-size:14px;color:#555;">
  Team Code: <strong style="font-family:monospace;">{{ team_code }}</strong>
</p>

<p style="margin:24px 0 0;font-size:13px;color:#6b7280;">
  Once all members have joined, lock the team from your dashboard to
  finalize registration.
</p>
{% endblock %}
"""


_TEAM_LOCKED = """{% extends "base" %}
{% block content %}
<p style="margin:0 0 16px;font-size:16px;">Hi <strong>{{ member_name }}</strong>,</p>
<p style="margin:0 0 20px;font-size:15px;color:#555;line-height:1.6;">
  Your team <strong>{{ team_name }}</strong> is now locked in for
  <strong>{{ event_name }}</strong>.
</p>

<p style="margin:16px 0;font-size:14px;color:#555;">
  Team Code: <strong style="font-family:monospace;">{{ team_code }}</strong>
</p>

<p style="margin:24px 0 0;font-size:13px;color:#6b7280;">
  See you at the event!
</p>
{% endblock %}
"""


_MEMBER_JOINED = """{% extends "base" %}
{% block content %}
<p style="margin:0 0 16px;font-size:16px;">Hi <strong>{{ member_name }}</strong>,</p>
<p style="margin:0 0 20px;font-size:15px;color:#555;line-height:1.6;">
  You have successfully joined team <strong>{{ team_name }}</strong> for
  <strong>{{ event_name }}</strong>.
</p>

<p style="margin:16px 0;font-size:14px;color:#555;">
  Team Lead: <strong>{{ leader_name }}</strong>
</p>

<p style="margin:24px 0 0;font-size:13px;color:#6b7280;">
  The team leader will finalize the registration once all members have
  joined. You'll get a confirmation email at that point.
</p>
{% endblock %}
"""


_ABSTRACT_UPLOAD_REQUEST = """{% extends "base" %}
{% block content %}
<p style="margin:0 0 16px;font-size:16px;">Hi <strong>{{ member_name }}</strong>,</p>
<p style="margin:0 0 20px;font-size:15px;color:#555;line-height:1.6;">
  Your team <strong>{{ team_name }}</strong> is locked for
  <strong>{{ event_name }}</strong>. The next step is abstract submission.
</p>

{% if abstract_deadline %}
<div style="margin:20px 0;padding:16px;background:#fee2e2;border:1px solid #fecaca;border-radius:8px;text-align:center;">
  <p style="margin:0 0 4px;font-size:12px;color:#991b1b;text-transform:uppercase;">Submission Deadline</p>
  <p style="margin:0;font-size:18px;font-weight:700;color:#991b1b;">{{ abstract_deadline }}</p>
</div>
{% endif %}

{% if is_leader %}
<p style="margin:16px 0;font-size:14px;color:#555;">
  As the team leader, upload the abstract from your dashboard before
  the deadline.
</p>
{% else %}
<p style="margin:16px 0;font-size:14px;color:#555;">
  Your team leader will upload the abstract. Please coordinate with them
  to ensure timely submission.
</p>
{% endif %}
{% endblock %}
"""


_PAPER_SELECTION_RESULT = """{% extends "base" %}
{% block content %}
<p style="margin:0 0 16px;font-size:16px;">Hi <strong>{{ member_name }}</strong>,</p>

{% if selection_status == "SELECTED" %}
<p style="margin:0 0 20px;font-size:15px;color:#166534;line-height:1.6;">
  <strong>Congratulations!</strong> Your team <strong>{{ team_name }}</strong>'s
  abstract for <strong>{{ event_name }}</strong> has been selected for presentation.
</p>

{% if presentation_deadline %}
<div style="margin:20px 0;padding:16px;background:#dcfce7;border:1px solid #bbf7d0;border-radius:8px;text-align:center;">
  <p style="margin:0 0 4px;font-size:12px;color:#166534;text-transform:uppercase;">Presentation Deadline</p>
  <p style="margin:0;font-size:18px;font-weight:700;color:#166534;">{{ presentation_deadline }}</p>
</div>
{% endif %}

<p style="margin:16px 0;font-size:14px;color:#555;">
  Prepare your presentation and upload it from your team dashboard before
  the deadline.
</p>
{% else %}
<p style="margin:0 0 20px;font-size:15px;color:#555;line-height:1.6;">
  Thank you for submitting your abstract for <strong>{{ event_name }}</strong>.
  After careful review, your abstract was not selected for presentation this
  time.
</p>

{% if selection_note %}
<div style="margin:16px 0;padding:12px 16px;background:#f3f4f6;border-left:3px solid #ef4444;border-radius:4px;">
  <p style="margin:0;font-size:13px;color:#6b7280;">Feedback from reviewers:</p>
  <p style="margin:6px 0 0;font-size:14px;color:#333;">{{ selection_note }}</p>
</div>
{% endif %}

<p style="margin:20px 0 0;font-size:14px;color:#555;">
  We appreciate your effort and encourage you to participate in other events.
</p>
{% endif %}
{% endblock %}
"""


_PASSWORD_RESET = """{% extends "base" %}
{% block content %}
<p style="margin:0 0 16px;font-size:16px;">Hi,</p>
<p style="margin:0 0 20px;font-size:15px;color:#555;line-height:1.6;">
  We received a request to reset the password for your Shackles Symposium
  account. Click the button below to choose a new one.
</p>

<div style="margin:24px 0;text-align:center;">
  <a href="{{ reset_url }}" style="display:inline-block;padding:12px 32px;background:#111827;color:#ffffff;text-decoration:none;border-radius:8px;font-size:14px;font-weight:600;">
    Reset Password
  </a>
</div>

<p style="margin:20px 0 0;font-size:13px;color:#6b7280;">
  This link expires in <strong>{{ expires_minutes }} minutes</strong>.
</p>

<p style="margin:8px 0 0;font-size:13px;color:#6b7280;">
  If you didn't request this, you can safely ignore this email. Your
  password will not change.
</p>
{% endblock %}
"""


_GENERIC = """{% extends "base" %}
{% block content %}
<p style="margin:0 0 16px;font-size:16px;">Hello,</p>
<p style="margin:0 0 20px;font-size:15px;color:#555;line-height:1.6;">
  {{ message }}
</p>
{% endblock %}
"""


# ============================================================
# Template registry + render function
# ============================================================

_TEMPLATES = {
    "base": _BASE,
    "payment_verified": _PAYMENT_VERIFIED,
    "team_created": _TEAM_CREATED,
    "team_locked": _TEAM_LOCKED,
    "member_joined": _MEMBER_JOINED,
    "abstract_upload_request": _ABSTRACT_UPLOAD_REQUEST,
    "paper_selection_result": _PAPER_SELECTION_RESULT,
    "password_reset": _PASSWORD_RESET,
    "generic": _GENERIC,
}


_env = Environment(
    loader=DictLoader(_TEMPLATES),
    autoescape=select_autoescape(["html", "xml"]),
)


def render_email_template(name: str, context: dict) -> str:
    """Render an email template by name.

    Unknown template names fall back to the generic template so jobs
    never fail due to a missing template.
    """
    template_name = name if name in _TEMPLATES else "generic"
    template = _env.get_template(template_name)

    ctx = {
        "subject": "Shackles Symposium",
        "year": context.get("year", ""),
        "message": "You have a new notification from Shackles Symposium.",
    }
    ctx.update(context)
    return template.render(**ctx)


def list_templates() -> list[str]:
    """Return available template names (for debugging)."""
    return [name for name in _TEMPLATES if name != "base"]