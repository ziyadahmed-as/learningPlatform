def migrate_data(apps, schema_editor):
    User = apps.get_model('users', 'User')
    Profile = apps.get_model('users', 'Profile')
    InstructorProfile = apps.get_model('users', 'InstructorProfile')
    StudentProfile = apps.get_model('users', 'StudentProfile')

    for user in User.objects.all():
        profile, _ = Profile.objects.get_or_create(user=user)
        profile.bio = user.bio
        profile.profile_picture = user.profile_picture
        profile.save()

        instr_profile, _ = InstructorProfile.objects.get_or_create(user=user)
        instr_profile.expertise = user.expertise
        instr_profile.education_level = user.education_level
        instr_profile.years_of_experience = user.years_of_experience
        instr_profile.cv_file = user.cv_file
        instr_profile.linkedin = user.linkedin
        instr_profile.portfolio = user.portfolio
        instr_profile.proposed_courses = user.proposed_courses
        instr_profile.is_approved_instructor = user.is_approved_instructor
        instr_profile.save()

        stud_profile, _ = StudentProfile.objects.get_or_create(user=user)
        stud_profile.points = user.points
        stud_profile.save()

class Migration(migrations.Migration):

    dependencies = [
        ('users', '0007_alter_user_role_instructorprofile_profile_and_more'),
    ]

    operations = [
        migrations.RunPython(migrate_data),
    ]
