import unittest

from src.audit import build_audit_payload


class AuditPayloadTests(unittest.TestCase):
    def test_wraps_text_content_in_a_message_field(self) -> None:
        self.assertEqual(build_audit_payload("completed"), {"message": "completed"})

    def test_preserves_structured_content(self) -> None:
        payload = {"response": "completed", "tool_count": 2}
        self.assertIs(build_audit_payload(payload), payload)


if __name__ == "__main__":
    unittest.main()
