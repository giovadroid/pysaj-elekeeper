from pysaj.crypto import encrypt_password, signed_params


def test_encrypt_password_matches_frontend_algorithm():
    assert encrypt_password("password") == "aaca15a3fa69f1467e2505455591ddcb"


def test_signed_params_matches_frontend_signature_chain(monkeypatch):
    class FixedDate:
        @classmethod
        def today(cls):
            return cls()

        def isoformat(self):
            return "2026-05-13"

    monkeypatch.setattr("pysaj.crypto.random_token", lambda: "ABCDEFGHJKMNPQRSTWXYZabcdefhi")
    monkeypatch.setattr("pysaj.crypto._timestamp_ms", lambda: 1778660000000)
    monkeypatch.setattr("pysaj.crypto.date", FixedDate)

    signed = signed_params({"pageNo": 1, "pageSize": 10})

    assert signed["signParams"] == (
        "pageNo,pageSize,appProjectName,clientDate,lang,timeStamp,random,clientId"
    )
    assert signed["signature"] == "77CE79CFCCB3B976E6FB72D045F8A4A5D39B59F6"
