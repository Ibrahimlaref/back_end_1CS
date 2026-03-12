from django.db import migrations

RLS_SQL = """
DO $$
DECLARE
    tbl TEXT;
    gym_tables TEXT[] := ARRAY[
        'user_gym_roles',
        'member_profiles',
        'coach_profiles',
        'coach_applications',
        'membership_plans',
        'subscriptions',
        'payments',
        'rooms',
        'courses',
        'reservations',
        'equipment',
        'maintenance_reports',
        'warnings',
        'products',
        'orders',
        'notifications',
        'messages',
        'activity_logs'
    ];
BEGIN
    FOREACH tbl IN ARRAY gym_tables
    LOOP
        IF to_regclass(tbl) IS NOT NULL THEN
            EXECUTE format('ALTER TABLE %I ENABLE ROW LEVEL SECURITY;', tbl);
            EXECUTE format('DROP POLICY IF EXISTS gym_isolation ON %I;', tbl);
            EXECUTE format($policy$
                CREATE POLICY gym_isolation ON %I
                USING (
                    current_setting('app.is_super_admin', true) = 'true'
                    OR gym_id = current_setting('app.current_gym_id')::uuid
                );
            $policy$, tbl);
        END IF;
    END LOOP;
END
$$;
"""

class Migration(migrations.Migration):

    dependencies = [
        ('core', '0002_initial'),
        ('gyms', '0002_initial'),
        ('membersNsubscription', '0001_initial'),
    ]

    operations = [
        migrations.RunSQL(RLS_SQL),
    ]
