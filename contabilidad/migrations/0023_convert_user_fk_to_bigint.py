# Generated manually to fix errno 150 (FK constraint mismatch)
# Django's auth app creates auth_user with integer PK, but DEFAULT_AUTO_FIELD is BigAutoField
# This migration converts auth_user.id to bigint BEFORE other apps create FKs to it

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('auth', '0012_alter_user_first_name_max_length'),
    ]

    run_before = [
        ('contabilidad', '0001_initial'),
        ('core', '0001_initial'),
    ]

    operations = [
        migrations.RunSQL(
            sql=[
                # Drop existing FKs that reference auth_user (from auth app tables)
                "ALTER TABLE `auth_user_groups` DROP FOREIGN KEY `auth_user_groups_user_id_6a12ed8b_fk_auth_user_id`",
                "ALTER TABLE `auth_user_user_permissions` DROP FOREIGN KEY `auth_user_user_permissions_user_id_a95ead1b_fk_auth_user_id`",
                "ALTER TABLE `django_admin_log` DROP FOREIGN KEY `django_admin_log_user_id_c564eba6_fk_auth_user_id`",

                # Convert auth_user.id to bigint
                "ALTER TABLE `auth_user` MODIFY `id` bigint AUTO_INCREMENT NOT NULL",

                # Convert FK columns to bigint
                "ALTER TABLE `auth_user_groups` MODIFY `user_id` bigint NOT NULL",
                "ALTER TABLE `auth_user_user_permissions` MODIFY `user_id` bigint NOT NULL",
                "ALTER TABLE `django_admin_log` MODIFY `user_id` bigint NOT NULL",

                # Re-add FKs
                "ALTER TABLE `auth_user_groups` ADD CONSTRAINT `auth_user_groups_user_id_6a12ed8b_fk_auth_user_id` FOREIGN KEY (`user_id`) REFERENCES `auth_user` (`id`)",
                "ALTER TABLE `auth_user_user_permissions` ADD CONSTRAINT `auth_user_user_permissions_user_id_a95ead1b_fk_auth_user_id` FOREIGN KEY (`user_id`) REFERENCES `auth_user` (`id`)",
                "ALTER TABLE `django_admin_log` ADD CONSTRAINT `django_admin_log_user_id_c564eba6_fk_auth_user_id` FOREIGN KEY (`user_id`) REFERENCES `auth_user` (`id`)",
            ],
            reverse_sql=[
                # Drop FKs
                "ALTER TABLE `auth_user_groups` DROP FOREIGN KEY `auth_user_groups_user_id_6a12ed8b_fk_auth_user_id`",
                "ALTER TABLE `auth_user_user_permissions` DROP FOREIGN KEY `auth_user_user_permissions_user_id_a95ead1b_fk_auth_user_id`",
                "ALTER TABLE `django_admin_log` DROP FOREIGN KEY `django_admin_log_user_id_c564eba6_fk_auth_user_id`",

                # Convert back to integer
                "ALTER TABLE `auth_user` MODIFY `id` integer AUTO_INCREMENT NOT NULL",
                "ALTER TABLE `auth_user_groups` MODIFY `user_id` integer NOT NULL",
                "ALTER TABLE `auth_user_user_permissions` MODIFY `user_id` integer NOT NULL",
                "ALTER TABLE `django_admin_log` MODIFY `user_id` integer NOT NULL",

                # Re-add FKs
                "ALTER TABLE `auth_user_groups` ADD CONSTRAINT `auth_user_groups_user_id_6a12ed8b_fk_auth_user_id` FOREIGN KEY (`user_id`) REFERENCES `auth_user` (`id`)",
                "ALTER TABLE `auth_user_user_permissions` ADD CONSTRAINT `auth_user_user_permissions_user_id_a95ead1b_fk_auth_user_id` FOREIGN KEY (`user_id`) REFERENCES `auth_user` (`id`)",
                "ALTER TABLE `django_admin_log` ADD CONSTRAINT `django_admin_log_user_id_c564eba6_fk_auth_user_id` FOREIGN KEY (`user_id`) REFERENCES `auth_user` (`id`)",
            ],
        ),
    ]
