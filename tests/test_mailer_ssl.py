"""Mailer escolhe SMTP_SSL na porta 465 e STARTTLS nas demais com use_tls."""

from __future__ import annotations

from types import SimpleNamespace

from worker.adapters import mailer


def test_send_report_email_uses_smtp_ssl_on_port_465(monkeypatch):
    calls: list[str] = []

    class FakeSSL:
        def __init__(self, *a, **k):
            calls.append("SMTP_SSL")

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def login(self, *a):
            calls.append("login")

        def send_message(self, msg, from_addr=None, to_addrs=None):
            calls.append(f"send:{msg['To']}|from={msg['From']}|reply={msg['Reply-To']}|env={from_addr}")

    class FakeSMTP:
        def __init__(self, *a, **k):
            calls.append("SMTP")

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def ehlo(self):
            return None

        def starttls(self):
            calls.append("starttls")

        def login(self, *a):
            calls.append("login")

        def send_message(self, msg, from_addr=None, to_addrs=None):
            calls.append(f"send:{msg['To']}|from={msg['From']}|reply={msg['Reply-To']}|env={from_addr}")

    monkeypatch.setattr(mailer.smtplib, "SMTP_SSL", FakeSSL)
    monkeypatch.setattr(mailer.smtplib, "SMTP", FakeSMTP)

    cfg = SimpleNamespace(
        smtp=SimpleNamespace(
            host="mail.example.com",
            port=465,
            username="u",
            use_tls=True,
            sender_email="from@example.com",
            sender_name="Portal",
            timeout_seconds=10,
        ),
        password="secret",
    )
    mailer.send_report_email(
        config=cfg,  # type: ignore[arg-type]
        subject="t",
        body="b",
        to_emails=["a@example.com"],
    )
    assert calls == [
        "SMTP_SSL",
        "login",
        "send:a@example.com|from=Portal <from@example.com>|reply=from@example.com|env=u",
    ]


def test_send_report_email_uses_starttls_on_port_587(monkeypatch):
    calls: list[str] = []

    class FakeSSL:
        def __init__(self, *a, **k):
            calls.append("SMTP_SSL")

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

    class FakeSMTP:
        def __init__(self, *a, **k):
            calls.append("SMTP")

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def ehlo(self):
            return None

        def starttls(self):
            calls.append("starttls")

        def login(self, *a):
            calls.append("login")

        def send_message(self, msg, from_addr=None, to_addrs=None):
            calls.append(f"send:{msg['To']}|from={msg['From']}|reply={msg['Reply-To']}|env={from_addr}")

    monkeypatch.setattr(mailer.smtplib, "SMTP_SSL", FakeSSL)
    monkeypatch.setattr(mailer.smtplib, "SMTP", FakeSMTP)

    cfg = SimpleNamespace(
        smtp=SimpleNamespace(
            host="mail.example.com",
            port=587,
            username="u",
            use_tls=True,
            sender_email="from@example.com",
            sender_name="Portal",
            timeout_seconds=10,
        ),
        password="secret",
    )
    mailer.send_report_email(
        config=cfg,  # type: ignore[arg-type]
        subject="t",
        body="b",
        to_emails=["a@example.com"],
    )
    assert calls == [
        "SMTP",
        "starttls",
        "login",
        "send:a@example.com|from=Portal <from@example.com>|reply=from@example.com|env=u",
    ]
