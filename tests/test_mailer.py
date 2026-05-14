from github_daily_report.mailer import EmailMessagePayload, send_report_email


def test_send_report_email_dry_run_does_not_connect():
    payload = EmailMessagePayload(
        subject="AI Daily",
        html="<html><body>Hello</body></html>",
        sender="from@example.com",
        recipients=["to@example.com"],
    )

    result = send_report_email(payload, smtp_config=None, dry_run=True)

    assert result.sent is False
    assert result.message == "dry-run"
