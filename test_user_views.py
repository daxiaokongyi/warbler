"""User View tests."""

# run these tests like:
#
#    FLASK_ENV=production python -m unittest test_message_views.py


import os
from unittest import TestCase

from models import db, connect_db, Message, User, Likes, Follows
from bs4 import BeautifulSoup

# BEFORE we import our app, let's set an environmental variable
# to use a different database for tests (we need to do this
# before we import our app, since that will have already
# connected to the database

os.environ['DATABASE_URL'] = "postgresql:///warbler-test"


# Now we can import app

from app import app, CURR_USER_KEY

# Create our tables (we do this here, so we only create the tables
# once for all tests --- in each test, we'll delete the data
# and create fresh new clean test data

db.create_all()

# Don't have WTForms use CSRF at all, since it's a pain to test

app.config['WTF_CSRF_ENABLED'] = False

class UserViewTestCase(TestCase):
    """test view of user"""
    def setUp(self):
        """Create test client, add sample data"""
        db.drop_all()
        db.create_all()

        self.client = app.test_client()
        self.testuser = User.signup("testuser", "test@email.com", "password", None)

        self.testuser_id = 8888
        self.testuser.id = self.testuser_id

        self.u1 = User.signup("u1", "u1@email.com", "password", None)
        self.u1_id = 900
        self.u1.id = self.u1_id
        self.u2 = User.signup("u2", "u2@email.com", "password", None)
        self.u2_id = 901
        self.u2.id = self.u2_id
        self.u3 = User.signup("u3", "u3@email.com", "password", None)
        self.u4 = User.signup("u4", "u4@email.com", "password", None)

        db.session.commit()

    def tearDown(self):
        resp = super().tearDown()
        db.session.rollback()
        return resp

    def test_users_index(self):
        with self.client as c:
            resp = c.get("/users")
        self.assertIn("u1", str(resp.data))
        self.assertIn("u2", str(resp.data))
        self.assertIn("u3", str(resp.data))
        self.assertIn("u4", str(resp.data))
        self.assertNotIn("u5", str(resp.data))

    def test_users_search(self):
        with self.client as c:
            resp = c.get("/users?q=u")
        self.assertIn("u1", str(resp.data))
        self.assertIn("u2", str(resp.data))
        self.assertIn("u3", str(resp.data))
        self.assertIn("u4", str(resp.data))
        self.assertNotIn("u5", str(resp.data))

    def test_user_show(self):
        with self.client as c:
            resp = c.get(f"/users/{self.testuser_id}")
        self.assertEqual(resp.status_code, 200)
        self.assertIn("testuser", str(resp.data))

# Setup likes
# ==========================================
    def setup_likes(self):
        m1 = Message(text="text1", user_id=self.testuser.id)
        m2 = Message(text="text2", user_id=self.testuser.id)
        m3 = Message(id= 707, text="likeable", user_id=self.u1.id)
        db.session.add_all([m1,m2,m3])
        db.session.commit()
        # give a like to test user's message
        l1=Likes(user_id=self.testuser.id, message_id=707)
        db.session.add(l1)
        db.session.commit()

    def test_user_show_with_likes(self):
        self.setup_likes()

        with self.client as c:
            resp = c.get(f"/users/{self.testuser_id}")

            # check status code
            self.assertEqual(resp.status_code, 200)
            self.assertIn("testuser", str(resp.data))
            soup = BeautifulSoup(str(resp.data), "html.parser")
            found=soup.find_all("li", {"class": "stat"})
            # import pdb
            # pdb.set_trace()
            self.assertEqual(len(found), 4)

            # test for a count of 2 messages
            self.assertIn("2", found[0].text)

            # Test for a count of 0 followers
            self.assertIn("0", found[1].text)

            # Test for a count of 0 following
            self.assertIn("0", found[2].text)

            # Test for a count of 1 like
            self.assertIn("1", found[3].text)

    def test_add_like(self):
        m = Message(id=121, text="message being liked", user_id=self.u1_id)
        db.session.add(m)
        db.session.commit()

        with self.client as c:
            with c.session_transaction() as sess:
                sess[CURR_USER_KEY] = self.testuser_id
            resp = c.post("/messages/121/like", follow_redirects=True)
            # import pdb
            # pdb.set_trace()
            self.assertEqual(resp.status_code, 200)
            # check all the users who like that message
            likes = Likes.query.filter(Likes.message_id == 121).all()
            self.assertEqual(len(likes), 1)
            # get authorized user
            testuser = User.query.get(self.testuser_id)
            self.assertEqual(likes[0].user_id, testuser.id)

    def test_remove_like(self):
        self.setup_likes()

        m_test = Message.query.filter(Message.user_id == self.testuser_id).all()
        # import pdb
        # pdb.set_trace()
        self.assertEqual(len(m_test),2)

        m1 = Message.query.filter(Message.user_id == self.u1_id).all()
        self.assertEqual(len(m1),1)

        m = Message.query.filter(Message.text == "likeable").all()
        self.assertEqual(len(m),1)

        likes = Likes.query.filter(Likes.user_id == self.testuser_id).all()
        self.assertEqual(len(likes),1)

        with self.client as c:
            with c.session_transaction() as sess:
                sess[CURR_USER_KEY] = self.testuser_id

            # Now remove the like by toggling the like botton with form
            resp = c.post(f"/messages/{m[0].id}/like", follow_redirects=True) 
            self.assertEqual(resp.status_code, 200)
            likes = Likes.query.filter(Likes.user_id == self.testuser_id).all()
            self.assertEqual(len(likes),0)
            # check if the toggle works for adding/removing likes
            resp = c.post(f"/messages/{m[0].id}/like", follow_redirects=True) 
            self.assertEqual(resp.status_code, 200)
            likes = Likes.query.filter(Likes.user_id == self.testuser_id).all()
            self.assertEqual(len(likes),1)
            
    def test_unauthenticated_like(self):
        self.setup_likes()
        m = Message.query.filter(Message.user_id == self.u1_id).all()
        self.assertEqual(len(m),1)

        # without autheticaion
        with self.client as c:
            resp = c.post(f"/messages/{m[0].id}/like", follow_redirects=True)
            self.assertEqual(resp.status_code, 200)
            # import pdb
            # pdb.set_trace()
            self.assertIn("Access unauthorized", str(resp.data))
            l = Likes.query.filter(Likes.user_id == self.testuser_id).all()
            self.assertEqual(len(m), len(l))

# Setup followers
# ==========================================
    def setup_followers(self):
        f1 = Follows(user_being_followed_id = self.u1_id, user_following_id=self.testuser_id)
        f2 = Follows(user_being_followed_id = self.u2_id, user_following_id=self.testuser_id)
        f3 = Follows(user_being_followed_id = self.testuser_id, user_following_id=self.u1_id)

        db.session.add_all([f1,f2,f3])
        db.session.commit()

    def test_user_show_with_follows(self):
        self.setup_followers()

        with self.client as c:
            resp = c.get(f'/users/{self.testuser_id}')
            self.assertEqual(resp.status_code, 200)
            self.assertIn("testuser", str(resp.data))
            soup = BeautifulSoup(str(resp.data),'html.parser')
            found = soup.find_all("li", {"class": "stat"})
            self.assertEqual(len(found), 4)
            
            # import pdb
            # pdb.set_trace()
            # test for a count of 0 messages
            self.assertIn("0", found[0].text)
            self.assertIn("Messages", found[0].text)

            # test for a count of 0 following
            self.assertIn("2", found[1].text)
            self.assertIn("Following", found[1].text)

            # test for a count of 0 follower
            self.assertIn("1", found[2].text)
            self.assertIn("Followers", found[2].text)

            # test for a count of 0 likes
            self.assertIn("0", found[3].text)
            self.assertIn("Likes", found[3].text)

    def test_show_following(self):
        self.setup_followers()
        with self.client as c:
            with c.session_transaction() as sess:
                sess[CURR_USER_KEY] = self.testuser_id

        resp = c.get(f"/users/{self.testuser_id}/following")
        self.assertEqual(resp.status_code, 200)
        self.assertIn("u1", str(resp.data))
        self.assertIn("u2", str(resp.data))
        
        resp = c.get(f"/users/{self.u1_id}/following")
        self.assertEqual(resp.status_code, 200)
        self.assertIn("testuser", str(resp.data))
        self.assertNotIn("u2", str(resp.data))

    def test_show_followers(self):
        self.setup_followers()
        with self.client as c:
            with c.session_transaction() as sess:
                sess[CURR_USER_KEY] = self.u1_id

        resp = c.get(f"/users/{self.u1_id}/followers")
        self.assertIn("testuser", str(resp.data))
        self.assertNotIn("u2", str(resp.data))

    def test_unauthorized_following_page_access(self):
        self.setup_followers()
        with self.client as c:
            resp = c.get(f"/users/{self.testuser_id}/following", follow_redirects=True)
            self.assertEqual(resp.status_code, 200)
            self.assertIn("Access unauthorized", str(resp.data))
            self.assertNotIn("u2", str(resp.data))

    def test_unauthorized_followers_page_access(self):
        self.setup_followers()
        with self.client as c:
            resp = c.get(f"/users/{self.testuser_id}/followers", follow_redirects=True)
            self.assertEqual(resp.status_code, 200)
            self.assertIn("Access unauthorized", str(resp.data))
            self.assertNotIn("u2", str(resp.data))  