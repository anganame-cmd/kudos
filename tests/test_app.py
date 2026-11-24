import unittest
from datetime import datetime, timedelta, timezone

from app import Kudos, User, create_app, db, seed_demo_users


class KudosAppTestCase(unittest.TestCase):
    def setUp(self):
        self.app = create_app(
            {
                "TESTING": True,
                "SECRET_KEY": "test-key",
                "SQLALCHEMY_DATABASE_URI": "sqlite://",
                "WTF_CSRF_ENABLED": False,
            }
        )
        self.app_context = self.app.app_context()
        self.app_context.push()
        db.create_all()
        seed_demo_users()
        self.client = self.app.test_client()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def user(self, username):
        return db.session.execute(
            db.select(User).where(User.username == username)
        ).scalar_one()

    def sign_in(self, username):
        response = self.client.post(
            "/demo/login", data={"user_id": self.user(username).id}
        )
        self.assertEqual(response.status_code, 302)

    def create_kudos(self, sender, recipient, message, **kwargs):
        kudos = Kudos(
            sender_user_id=sender.id,
            recipient_user_id=recipient.id,
            message=message,
            **kwargs,
        )
        db.session.add(kudos)
        db.session.commit()
        return kudos

    def test_seeded_demo_users_include_an_administrator(self):
        users = db.session.execute(db.select(User)).scalars().all()
        self.assertEqual(len(users), 4)
        self.assertTrue(self.user("admin").is_admin)
        self.assertFalse(self.user("alex").is_admin)

    def test_dashboard_requires_demo_sign_in(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 302)
        self.assertIn("/demo/login", response.headers["Location"])

    def test_demo_login_and_recipient_selector_render(self):
        login_page = self.client.get("/demo/login")
        self.assertEqual(login_page.status_code, 200)
        self.assertIn("Demo Administrator", login_page.get_data(as_text=True))

        self.sign_in("alex")
        form_page = self.client.get("/kudos/new")
        body = form_page.get_data(as_text=True)
        self.assertEqual(form_page.status_code, 200)
        self.assertIn('id="recipient-search"', body)
        self.assertNotIn(f'value="{self.user("alex").id}"', body)
        self.assertIn(f'value="{self.user("jordan").id}"', body)

    def test_deactivated_user_session_is_rejected(self):
        self.sign_in("alex")
        alex = self.user("alex")
        alex.is_active = False
        db.session.commit()

        response = self.client.get("/")

        self.assertEqual(response.status_code, 302)
        self.assertIn("/demo/login", response.headers["Location"])

    def test_visible_feed_is_newest_first_and_excludes_hidden_kudos(self):
        self.sign_in("alex")
        alex = self.user("alex")
        jordan = self.user("jordan")
        earlier = self.create_kudos(
            alex, jordan, "Earlier", created_at=datetime.now(timezone.utc) - timedelta(days=1)
        )
        latest = self.create_kudos(alex, jordan, "Latest")
        hidden = self.create_kudos(alex, jordan, "Hidden", is_visible=False)
        shared = self.create_kudos(jordan, self.user("casey"), "Visible to everyone")

        response = self.client.get("/")
        body = response.get_data(as_text=True)
        self.assertEqual(response.status_code, 200)
        self.assertLess(body.index("Latest"), body.index("Earlier"))
        self.assertNotIn("Hidden", body)
        self.assertIn("Alex Rivera", body)
        self.assertIn("Jordan Lee", body)
        self.assertIn("Visible to everyone", body)
        self.assertNotEqual(earlier.id, latest.id)
        self.assertFalse(hidden.is_visible)
        self.assertEqual(shared.sender.username, "jordan")

    def test_feed_paginates_visible_entries_without_skipping(self):
        self.sign_in("alex")
        alex = self.user("alex")
        jordan = self.user("jordan")
        base_time = datetime(2026, 1, 1, tzinfo=timezone.utc)
        for index in range(21):
            self.create_kudos(
                alex,
                jordan,
                f"Entry {index}",
                created_at=base_time + timedelta(seconds=index),
            )

        first_page = self.client.get("/")
        second_page = self.client.get("/?page=2")
        first_body = first_page.get_data(as_text=True)
        second_body = second_page.get_data(as_text=True)

        self.assertEqual(first_page.status_code, 200)
        self.assertEqual(second_page.status_code, 200)
        self.assertIn("Entry 20", first_body)
        self.assertIn("Entry 1", first_body)
        self.assertNotIn("Entry 0", first_body)
        self.assertIn("Entry 0", second_body)
        self.assertNotIn("Entry 1", second_body)

    def test_submission_creates_kudos_for_selected_colleague(self):
        self.sign_in("alex")
        recipient = self.user("jordan")

        response = self.client.post(
            "/kudos/new",
            data={"recipient_id": recipient.id, "message": "Thanks for your help!"},
        )

        self.assertEqual(response.status_code, 302)
        kudos = db.session.execute(db.select(Kudos)).scalar_one()
        self.assertEqual(kudos.sender.username, "alex")
        self.assertEqual(kudos.recipient.username, "jordan")
        self.assertEqual(kudos.message, "Thanks for your help!")
        self.assertTrue(kudos.is_visible)

    def test_submission_rejects_blank_long_self_and_inactive_recipients(self):
        self.sign_in("alex")
        alex = self.user("alex")
        jordan = self.user("jordan")
        casey = self.user("casey")
        casey.is_active = False
        db.session.commit()

        invalid_submissions = [
            {"recipient_id": jordan.id, "message": "   "},
            {"recipient_id": jordan.id, "message": "x" * 501},
            {"recipient_id": alex.id, "message": "Self kudos"},
            {"recipient_id": casey.id, "message": "Inactive recipient"},
            {"recipient_id": 999999, "message": "Unknown recipient"},
        ]
        for submission in invalid_submissions:
            with self.subTest(submission=submission):
                response = self.client.post("/kudos/new", data=submission)
                self.assertEqual(response.status_code, 400)
        self.assertEqual(db.session.scalar(db.select(db.func.count(Kudos.id))), 0)

    def test_message_is_rendered_as_escaped_text(self):
        self.sign_in("alex")
        self.client.post(
            "/kudos/new",
            data={
                "recipient_id": self.user("jordan").id,
                "message": "<script>alert(1)</script>",
            },
        )

        body = self.client.get("/").get_data(as_text=True)
        self.assertIn("&lt;script&gt;alert(1)&lt;/script&gt;", body)
        self.assertNotIn("<script>alert(1)</script>", body)

    def test_non_administrator_cannot_view_or_moderate_kudos(self):
        self.sign_in("alex")
        kudos = self.create_kudos(
            self.user("alex"), self.user("jordan"), "Keep this visible"
        )

        self.assertEqual(self.client.get("/admin/kudos").status_code, 403)
        self.assertEqual(
            self.client.post(f"/admin/kudos/{kudos.id}/hide").status_code, 403
        )
        self.assertTrue(db.session.get(Kudos, kudos.id).is_visible)

    def test_administrator_can_hide_and_delete_kudos(self):
        admin = self.user("admin")
        alex = self.user("alex")
        jordan = self.user("jordan")
        hidden = self.create_kudos(alex, jordan, "Hidden by admin")
        deleted = self.create_kudos(alex, jordan, "Deleted by admin")
        self.sign_in("admin")

        moderation_page = self.client.get("/admin/kudos")
        self.assertEqual(moderation_page.status_code, 200)
        self.assertIn("Hidden by admin", moderation_page.get_data(as_text=True))

        hide_response = self.client.post(f"/admin/kudos/{hidden.id}/hide")
        self.assertEqual(hide_response.status_code, 302)
        self.assertFalse(db.session.get(Kudos, hidden.id).is_visible)
        self.assertNotIn("Hidden by admin", self.client.get("/").get_data(as_text=True))

        delete_response = self.client.post(f"/admin/kudos/{deleted.id}/delete")
        self.assertEqual(delete_response.status_code, 302)
        self.assertIsNone(db.session.get(Kudos, deleted.id))
        self.assertTrue(admin.is_admin)

    def test_demo_auth_is_rejected_outside_local_environment(self):
        with self.assertRaises(RuntimeError):
            create_app(
                {
                    "KUDOS_ENV": "production",
                    "SQLALCHEMY_DATABASE_URI": "sqlite://",
                }
            )

    def test_login_post_requires_csrf_token(self):
        csrf_app = create_app(
            {
                "TESTING": True,
                "SECRET_KEY": "csrf-test-key",
                "SQLALCHEMY_DATABASE_URI": "sqlite://",
                "WTF_CSRF_ENABLED": True,
            }
        )
        with csrf_app.app_context():
            db.create_all()
            seed_demo_users()

        response = csrf_app.test_client().post(
            "/demo/login",
            data={"user_id": 1},
        )
        self.assertEqual(response.status_code, 400)

        with csrf_app.app_context():
            db.session.remove()
            db.drop_all()


if __name__ == "__main__":
    unittest.main()
