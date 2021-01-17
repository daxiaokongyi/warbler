import os
from unittest import TestCase
from sqlalchemy import exc

from models import db, User, Message, Follows, Likes

os.environ['DATABASE_URL'] = "postgresql:///warbler-test"

from app import app

db.create_all()

class UserModelTestCase(TestCase):
    def setUp(self):
        """Create test client, add sample data."""
        db.drop_all()
        db.create_all()

        u = User.signup("test", "test@email.com", "password", None)
        self.uid = 666  
        u.id = self.uid

        db.session.commit()

        self.u = User.query.get_or_404(self.uid)
        self.client = app.test_client()

    def tearDown(self):
        res = super().tearDown()
        db.session.rollback()
        return res

    def test_message_model(self):
        """Does Basic model work?"""
        m = Message(text="test", user_id = self.uid)
        
        db.session.add(m)
        db.session.commit()

        # user should have one message
        self.assertIsNotNone(m.user)
        self.assertEqual(len(self.u.messages), 1)
        self.assertEqual(self.u.messages[0].text, "test")
        self.assertEqual(m.user, self.u)

    def test_message_likes(self):
        """Check likes"""
        m1 = Message(text="test1", user_id = self.uid)
        m2 = Message(text="test2", user_id = self.uid)
        m3 = Message(text="test3", user_id = self.uid)

        db.session.add_all([m1,m2,m3])
        db.session.commit()

        self.u.likes.append(m1)
        self.u.likes.append(m2)

        db.session.commit()

        l = Likes.query.filter(Likes.user_id == self.u.id).all()
        self.assertEqual(len(l),2)
        self.assertTrue(l[0].user_id == self.u.id)
