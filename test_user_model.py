"""User model tests."""

# run these tests like:
#
#    python -m unittest test_user_model.py


import os
from unittest import TestCase
from sqlalchemy import exc
from models import db, User, Message, Follows

# BEFORE we import our app, let's set an environmental variable
# to use a different database for tests (we need to do this
# before we import our app, since that will have already
# connected to the database

os.environ['DATABASE_URL'] = "postgresql:///warbler-test"


# Now we can import app

from app import app

# Create our tables (we do this here, so we only create the tables
# once for all tests --- in each test, we'll delete the data
# and create fresh new clean test data

db.create_all()


class UserModelTestCase(TestCase):
    """Test views for messages."""

    def setUp(self):
        """Create test client, add sample data."""
        db.drop_all()
        db.create_all()

        # User.query.delete()
        # Message.query.delete()
        # Follows.query.delete()

        u1 = User.signup('test1', 'test1@email.com', 'password', None)
        u1id = 1111
        u1.id = u1id

        u2 = User.signup('test2', 'test2@email.com', 'password', None)
        u2id = 2222
        u2.id = u2id

        db.session.commit()

        # get user one and user two
        u1 = User.query.get(u1id)
        u2 = User.query.get(u2id)

        self.u1 = u1
        self.u1id = u1id

        self.u2 = u2
        self.u2id = u2id

        self.client = app.test_client()

    def tearDown(self):
        res = super().tearDown()
        db.session.rollback()
        return res

    def test_user_model(self):
        """Does basic model work?"""

        u = User(
            email="test@test.com",
            username="testuser",
            password="HASHED_PASSWORD"
        )

        db.session.add(u)
        db.session.commit()

        # User should have no messages & no followers
        self.assertEqual(len(u.messages), 0)
        self.assertEqual(len(u.followers), 0)

    # Following Tests
    # ===================================================================================

    def test_user_follows(self):
        """Check if following and follwers works"""
        self.u1.following.append(self.u2)
        db.session.commit()

        self.assertEqual(len(self.u1.following), 1)
        self.assertEqual(len(self.u1.followers), 0)
        self.assertEqual(len(self.u2.following), 0)
        self.assertEqual(len(self.u2.followers), 1)

        self.assertEqual(self.u2.followers[0].id, self.u1.id)
        self.assertEqual(self.u1.following[0].id, self.u2.id)

    def test_is_following(self):
        """check if the class method of is_following works"""
        self.u1.following.append(self.u2)
        self.assertTrue(self.u1.is_following(self.u2))
        self.assertFalse(self.u2.is_following(self.u1))

    def test_is_followed(self):
        """check if the class method of is_followed_by works"""
        self.u1.following.append(self.u2)
        self.assertFalse(self.u1.is_followed_by(self.u2))
        self.assertTrue(self.u2.is_followed_by(self.u1))

    # ===================================================================================

    # Signup Tests
    # ===================================================================================

    def test_valid_signup(self):
        u_test = User.signup("test", "test@email.com", "password", None)
        uid = 9999
        u_test.id = uid

        db.session.commit()

        test_user = User.query.get_or_404(uid)
        self.assertIsNotNone(test_user)
        self.assertEqual(test_user.username, "test")
        self.assertEqual(test_user.email, "test@email.com")
        self.assertNotEqual(test_user.password, "password")
        self.assertTrue(test_user.password.startswith("$2b$"))

    def test_invalid_username_signup(self):
        invalid_user = User.signup(None, "test@test.com", "password", None)
        user_id = 123
        invalid_user.id = user_id
        with self.assertRaises(exc.IntegrityError) as context:
            db.session.commit()

    def test_invalid_email_signup(self):
        invalid_user = User.signup("Test", None, "password", None)
        user_id = 123
        invalid_user.id = user_id
        with self.assertRaises(exc.IntegrityError) as context:
            db.session.commit()

    def test_invalid_password_signup(self):
        with self.assertRaises(ValueError) as context:
            User.signup("Test", "Test@email.com", "", None)
        with self.assertRaises(ValueError) as context:
            User.signup("Test", "Test@email.com", None, None)

    # Authentication Tests
    # ===================================================================================
    def test_valid_authentication(self):
        u = User.authenticate(self.u1.username, "password")
        self.assertIsNotNone(u)
        self.assertEqual(u.id, self.u1.id)

    def test_invalid_username(self):
        u = User.authenticate("invalidname", "password")
        self.assertFalse(u)

    def test_invalid_password(self):
        u = User.authenticate(self.u1.username, "pass")
        self.assertEqual(u, False)