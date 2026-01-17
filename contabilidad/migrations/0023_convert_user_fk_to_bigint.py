# Generated manually to fix errno 150 (FK constraint mismatch)
# Django's built-in app migrations create tables with integer PKs, but DEFAULT_AUTO_FIELD is BigAutoField
# This converts ALL Django base tables to bigint BEFORE contabilidad/core create FKs to them

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('auth', '0012_alter_user_first_name_max_length'),
        ('contenttypes', '0002_remove_content_type_name'),
    ]

    run_before = [
        ('contabilidad', '0001_initial'),
        ('core', '0001_initial'),
    ]

    operations = [
        migrations.RunSQL(
            sql=[
                # === 1. DJANGO_CONTENT_TYPE ===
                "ALTER TABLE `auth_permission` DROP FOREIGN KEY `auth_permission_content_type_id_2f476e4b_fk_django_co`",
                "ALTER TABLE `django_admin_log` DROP FOREIGN KEY `django_admin_log_content_type_id_c4bce8eb_fk_django_co`",

                "ALTER TABLE `django_content_type` MODIFY `id` bigint AUTO_INCREMENT NOT NULL",
                "ALTER TABLE `auth_permission` MODIFY `content_type_id` bigint NOT NULL",
                "ALTER TABLE `django_admin_log` MODIFY `content_type_id` bigint NULL",

                "ALTER TABLE `auth_permission` ADD CONSTRAINT `auth_permission_content_type_id_2f476e4b_fk_django_co` FOREIGN KEY (`content_type_id`) REFERENCES `django_content_type` (`id`)",
                "ALTER TABLE `django_admin_log` ADD CONSTRAINT `django_admin_log_content_type_id_c4bce8eb_fk_django_co` FOREIGN KEY (`content_type_id`) REFERENCES `django_content_type` (`id`)",

                # === 2. AUTH_PERMISSION ===
                "ALTER TABLE `auth_group_permissions` DROP FOREIGN KEY `auth_group_permissions_permission_id_84c5c92e_fk_auth_perm`",
                "ALTER TABLE `auth_user_user_permissions` DROP FOREIGN KEY `auth_user_user_permissions_permission_id_1fbb5f2c_fk_auth_perm`",

                "ALTER TABLE `auth_permission` MODIFY `id` bigint AUTO_INCREMENT NOT NULL",
                "ALTER TABLE `auth_group_permissions` MODIFY `permission_id` bigint NOT NULL",
                "ALTER TABLE `auth_user_user_permissions` MODIFY `permission_id` bigint NOT NULL",

                "ALTER TABLE `auth_group_permissions` ADD CONSTRAINT `auth_group_permissions_permission_id_84c5c92e_fk_auth_perm` FOREIGN KEY (`permission_id`) REFERENCES `auth_permission` (`id`)",
                "ALTER TABLE `auth_user_user_permissions` ADD CONSTRAINT `auth_user_user_permissions_permission_id_1fbb5f2c_fk_auth_perm` FOREIGN KEY (`permission_id`) REFERENCES `auth_permission` (`id`)",

                # === 3. AUTH_GROUP ===
                "ALTER TABLE `auth_group_permissions` DROP FOREIGN KEY `auth_group_permissions_group_id_b120cbf9_fk_auth_group_id`",
                "ALTER TABLE `auth_user_groups` DROP FOREIGN KEY `auth_user_groups_group_id_97559544_fk_auth_group_id`",

                "ALTER TABLE `auth_group` MODIFY `id` bigint AUTO_INCREMENT NOT NULL",
                "ALTER TABLE `auth_group_permissions` MODIFY `group_id` bigint NOT NULL",
                "ALTER TABLE `auth_user_groups` MODIFY `group_id` bigint NOT NULL",

                "ALTER TABLE `auth_group_permissions` ADD CONSTRAINT `auth_group_permissions_group_id_b120cbf9_fk_auth_group_id` FOREIGN KEY (`group_id`) REFERENCES `auth_group` (`id`)",
                "ALTER TABLE `auth_user_groups` ADD CONSTRAINT `auth_user_groups_group_id_97559544_fk_auth_group_id` FOREIGN KEY (`group_id`) REFERENCES `auth_group` (`id`)",

                # === 4. AUTH_USER ===
                "ALTER TABLE `auth_user_groups` DROP FOREIGN KEY `auth_user_groups_user_id_6a12ed8b_fk_auth_user_id`",
                "ALTER TABLE `auth_user_user_permissions` DROP FOREIGN KEY `auth_user_user_permissions_user_id_a95ead1b_fk_auth_user_id`",
                "ALTER TABLE `django_admin_log` DROP FOREIGN KEY `django_admin_log_user_id_c564eba6_fk_auth_user_id`",

                "ALTER TABLE `auth_user` MODIFY `id` bigint AUTO_INCREMENT NOT NULL",
                "ALTER TABLE `auth_user_groups` MODIFY `user_id` bigint NOT NULL",
                "ALTER TABLE `auth_user_user_permissions` MODIFY `user_id` bigint NOT NULL",
                "ALTER TABLE `django_admin_log` MODIFY `user_id` bigint NOT NULL",

                "ALTER TABLE `auth_user_groups` ADD CONSTRAINT `auth_user_groups_user_id_6a12ed8b_fk_auth_user_id` FOREIGN KEY (`user_id`) REFERENCES `auth_user` (`id`)",
                "ALTER TABLE `django_admin_log` ADD CONSTRAINT `django_admin_log_user_id_c564eba6_fk_auth_user_id` FOREIGN KEY (`user_id`) REFERENCES `auth_user` (`id`)",
            ],
            reverse_sql=[
                # === Reverse order: user -> group -> permission -> content_type ===

                # AUTH_USER
                "ALTER TABLE `auth_user_groups` DROP FOREIGN KEY `auth_user_groups_user_id_6a12ed8b_fk_auth_user_id`",
                "ALTER TABLE `auth_user_user_permissions` DROP FOREIGN KEY `auth_user_user_permissions_user_id_a95ead1b_fk_auth_user_id`",
                "ALTER TABLE `django_admin_log` DROP FOREIGN KEY `django_admin_log_user_id_c564eba6_fk_auth_user_id`",

                "ALTER TABLE `auth_user` MODIFY `id` integer AUTO_INCREMENT NOT NULL",
                "ALTER TABLE `auth_user_groups` MODIFY `user_id` integer NOT NULL",
                "ALTER TABLE `auth_user_user_permissions` MODIFY `user_id` integer NOT NULL",
                "ALTER TABLE `django_admin_log` MODIFY `user_id` integer NOT NULL",

                "ALTER TABLE `auth_user_groups` ADD CONSTRAINT `auth_user_groups_user_id_6a12ed8b_fk_auth_user_id` FOREIGN KEY (`user_id`) REFERENCES `auth_user` (`id`)",
                "ALTER TABLE `auth_user_user_permissions` ADD CONSTRAINT `auth_user_user_permissions_user_id_a95ead1b_fk_auth_user_id` FOREIGN KEY (`user_id`) REFERENCES `auth_user` (`id`)",
                "ALTER TABLE `django_admin_log` ADD CONSTRAINT `django_admin_log_user_id_c564eba6_fk_auth_user_id` FOREIGN KEY (`user_id`) REFERENCES `auth_user` (`id`)",

                # AUTH_GROUP
                "ALTER TABLE `auth_group_permissions` DROP FOREIGN KEY `auth_group_permissions_group_id_b120cbf9_fk_auth_group_id`",
                "ALTER TABLE `auth_user_groups` DROP FOREIGN KEY `auth_user_groups_group_id_97559544_fk_auth_group_id`",

                "ALTER TABLE `auth_group` MODIFY `id` integer AUTO_INCREMENT NOT NULL",
                "ALTER TABLE `auth_group_permissions` MODIFY `group_id` integer NOT NULL",
                "ALTER TABLE `auth_user_groups` MODIFY `group_id` integer NOT NULL",

                "ALTER TABLE `auth_group_permissions` ADD CONSTRAINT `auth_group_permissions_group_id_b120cbf9_fk_auth_group_id` FOREIGN KEY (`group_id`) REFERENCES `auth_group` (`id`)",
                "ALTER TABLE `auth_user_groups` ADD CONSTRAINT `auth_user_groups_group_id_97559544_fk_auth_group_id` FOREIGN KEY (`group_id`) REFERENCES `auth_group` (`id`)",

                # AUTH_PERMISSION
                "ALTER TABLE `auth_group_permissions` DROP FOREIGN KEY `auth_group_permissions_permission_id_84c5c92e_fk_auth_perm`",
                "ALTER TABLE `auth_user_user_permissions` DROP FOREIGN KEY `auth_user_user_permissions_permission_id_1fbb5f2c_fk_auth_perm`",

                "ALTER TABLE `auth_permission` MODIFY `id` integer AUTO_INCREMENT NOT NULL",
                "ALTER TABLE `auth_group_permissions` MODIFY `permission_id` integer NOT NULL",
                "ALTER TABLE `auth_user_user_permissions` MODIFY `permission_id` integer NOT NULL",

                "ALTER TABLE `auth_group_permissions` ADD CONSTRAINT `auth_group_permissions_permission_id_84c5c92e_fk_auth_perm` FOREIGN KEY (`permission_id`) REFERENCES `auth_permission` (`id`)",
                "ALTER TABLE `auth_user_user_permissions` ADD CONSTRAINT `auth_user_user_permissions_permission_id_1fbb5f2c_fk_auth_perm` FOREIGN KEY (`permission_id`) REFERENCES `auth_permission` (`id`)",

                # DJANGO_CONTENT_TYPE
                "ALTER TABLE `auth_permission` DROP FOREIGN KEY `auth_permission_content_type_id_2f476e4b_fk_django_co`",
                "ALTER TABLE `django_admin_log` DROP FOREIGN KEY `django_admin_log_content_type_id_c4bce8eb_fk_django_co`",

                "ALTER TABLE `django_content_type` MODIFY `id` integer AUTO_INCREMENT NOT NULL",
                "ALTER TABLE `auth_permission` MODIFY `content_type_id` integer NOT NULL",
                "ALTER TABLE `django_admin_log` MODIFY `content_type_id` integer NULL",

                "ALTER TABLE `auth_permission` ADD CONSTRAINT `auth_permission_content_type_id_2f476e4b_fk_django_co` FOREIGN KEY (`content_type_id`) REFERENCES `django_content_type` (`id`)",
                "ALTER TABLE `django_admin_log` ADD CONSTRAINT `django_admin_log_content_type_id_c4bce8eb_fk_django_co` FOREIGN KEY (`content_type_id`) REFERENCES `django_content_type` (`id`)",
            ],
        ),
    ]
