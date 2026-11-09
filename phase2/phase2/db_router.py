from django.conf import settings


class PrimaryReplicaRouter:
    """Route ORM writes to the primary and reads to an optional replica."""

    def db_for_read(self, model, **hints):
        if 'read_replica' in settings.DATABASES:
            return 'read_replica'
        return 'default'

    def db_for_write(self, model, **hints):
        return 'default'

    def allow_relation(self, obj1, obj2, **hints):
        if obj1._state.db == obj2._state.db:
            return True
        return None

    def allow_migrate(self, db, app_label, model_name=None, **hints):
        return db == 'default'
