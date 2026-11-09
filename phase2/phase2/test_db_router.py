from django.test import SimpleTestCase, override_settings

from phase2.db_router import PrimaryReplicaRouter


class PrimaryReplicaRouterTests(SimpleTestCase):
    def setUp(self):
        self.router = PrimaryReplicaRouter()

    def test_reads_use_configured_replica(self):
        with override_settings(DATABASES={
            'default': {'ENGINE': 'django.db.backends.sqlite3', 'NAME': ':memory:'},
            'read_replica': {
                'ENGINE': 'django.db.backends.sqlite3',
                'NAME': ':memory:',
            },
        }):
            self.assertEqual(self.router.db_for_read(object), 'read_replica')

    def test_reads_fall_back_to_primary_without_replica(self):
        with override_settings(DATABASES={
            'default': {'ENGINE': 'django.db.backends.sqlite3', 'NAME': ':memory:'},
        }):
            self.assertEqual(self.router.db_for_read(object), 'default')

    def test_writes_and_migrations_are_primary_only(self):
        self.assertEqual(self.router.db_for_write(object), 'default')
        self.assertTrue(self.router.allow_migrate('default', 'patients'))
        self.assertFalse(self.router.allow_migrate('read_replica', 'patients'))
        self.assertFalse(self.router.allow_migrate('analytics', 'patients'))
