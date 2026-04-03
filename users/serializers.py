from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from .models import Profile, InstructorProfile, StudentProfile

User = get_user_model()

class UserSerializer(serializers.ModelSerializer):
    signal_strength = serializers.SerializerMethodField()
    peer_ranking = serializers.SerializerMethodField()

    def get_signal_strength(self, obj):
        return "100%" if obj.is_active else "0%"

    def get_peer_ranking(self, obj):
        total_users = User.objects.count()
        if total_users <= 1:
            return "TOP 1%"
        try:
            points = obj.student_profile.points
        except:
            points = 0
        better_users = User.objects.filter(student_profile__points__gt=points).count()
        rank_percent = int((better_users / total_users) * 100)
        if rank_percent < 1: return "TOP 1%"
        return f"TOP {rank_percent}%"

    class Meta:
        model = User
        fields = (
            'id', 'username', 'email', 'role', 'is_superuser', 'bio', 'profile_picture', 
            'first_name', 'last_name', 'expertise', 'education_level', 
            'years_of_experience', 'linkedin', 'portfolio', 
            'proposed_courses', 'cv_file', 'is_approved_instructor', 'points', 'signal_strength', 'peer_ranking'
        )
        read_only_fields = ('id', 'role', 'is_superuser', 'is_approved_instructor', 'signal_strength', 'peer_ranking')

    def update(self, instance, validated_data):
        profile_data = validated_data.pop('profile', {})
        instructor_data = validated_data.pop('instructor_profile', {})
        
        # Update User
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        # Update Profile
        if profile_data:
            profile = instance.profile
            for attr, value in profile_data.items():
                setattr(profile, attr, value)
            profile.save()

        # Update InstructorProfile
        if instructor_data:
            instr_profile = instance.instructor_profile
            for attr, value in instructor_data.items():
                setattr(instr_profile, attr, value)
            instr_profile.save()

        return instance

class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=True, validators=[validate_password])
    password_confirm = serializers.CharField(write_only=True, required=True)
    
    bio = serializers.CharField(required=False, allow_blank=True)
    expertise = serializers.CharField(required=False, allow_blank=True)
    education_level = serializers.CharField(required=False, allow_blank=True)
    years_of_experience = serializers.IntegerField(required=False, default=0)
    linkedin = serializers.URLField(required=False, allow_blank=True)
    portfolio = serializers.URLField(required=False, allow_blank=True)
    proposed_courses = serializers.CharField(required=False, allow_blank=True)
    cv_file = serializers.FileField(required=False, allow_null=True)

    class Meta:
        model = User
        fields = ('username', 'email', 'password', 'password_confirm', 'first_name', 'last_name',
                  'role', 'expertise', 'education_level', 'years_of_experience', 'bio', 
                  'linkedin', 'portfolio', 'proposed_courses', 'cv_file')

    def validate(self, attrs):
        if attrs['password'] != attrs['password_confirm']:
            raise serializers.ValidationError({"password": "Password fields didn't match."})
        return attrs

    def create(self, validated_data):
        password = validated_data.pop('password')
        validated_data.pop('password_confirm')
        
        # Extract profile/instructor data
        bio = validated_data.pop('bio', '')
        expertise = validated_data.pop('expertise', '')
        education_level = validated_data.pop('education_level', '')
        years_of_experience = validated_data.pop('years_of_experience', 0)
        linkedin = validated_data.pop('linkedin', '')
        portfolio = validated_data.pop('portfolio', '')
        proposed_courses = validated_data.pop('proposed_courses', '')
        cv_file = validated_data.pop('cv_file', None)

        user = User.objects.create_user(
            password=password,
            **validated_data
        )
        
        # Update profiles (already created by signal)
        profile = user.profile
        profile.bio = bio
        profile.save()
        
        instr_profile = user.instructor_profile
        instr_profile.expertise = expertise
        instr_profile.education_level = education_level
        instr_profile.years_of_experience = years_of_experience
        instr_profile.linkedin = linkedin
        instr_profile.portfolio = portfolio
        instr_profile.proposed_courses = proposed_courses
        instr_profile.cv_file = cv_file
        instr_profile.save()
        
        return user

from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

class MyTokenObtainPairSerializer(TokenObtainPairSerializer):
    def validate(self, attrs):
        # We allow login with either username or email
        username_or_email = attrs.get('username')
        password = attrs.get('password')
        
        # Try to find the user by email first if it looks like one
        if '@' in username_or_email:
            try:
                user = User.objects.get(email=username_or_email)
                # If found, set the 'username' to the actual username for the standard auth logic
                attrs['username'] = user.username
            except User.DoesNotExist:
                pass # Default logic will handle it (and likely return 401)
                
        data = super().validate(attrs)
        # Add user data to response
        data['user'] = UserSerializer(self.user).data
        return data

class AdminUserSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=False, validators=[validate_password])
    
    bio = serializers.CharField(source='profile.bio', allow_blank=True, required=False)
    profile_picture = serializers.ImageField(source='profile.profile_picture', required=False, allow_null=True)
    expertise = serializers.CharField(source='instructor_profile.expertise', allow_blank=True, required=False)
    education_level = serializers.CharField(source='instructor_profile.education_level', allow_blank=True, required=False)
    years_of_experience = serializers.IntegerField(source='instructor_profile.years_of_experience', required=False)
    cv_file = serializers.FileField(source='instructor_profile.cv_file', required=False, allow_null=True)
    linkedin = serializers.URLField(source='instructor_profile.linkedin', allow_blank=True, required=False)
    portfolio = serializers.URLField(source='instructor_profile.portfolio', allow_blank=True, required=False)
    proposed_courses = serializers.CharField(source='instructor_profile.proposed_courses', allow_blank=True, required=False)
    is_approved_instructor = serializers.BooleanField(source='instructor_profile.is_approved_instructor', required=False)
    points = serializers.IntegerField(source='student_profile.points', required=False)
    
    enrolled_courses = serializers.SerializerMethodField()
    taught_courses = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = (
            'id', 'username', 'email', 'password', 'role', 'bio', 
            'profile_picture', 'first_name', 'last_name', 'expertise', 
            'education_level', 'years_of_experience', 'linkedin', 
            'portfolio', 'proposed_courses', 'cv_file', 'is_approved_instructor', 'points',
            'enrolled_courses', 'taught_courses'
        )
        read_only_fields = ('id', 'enrolled_courses', 'taught_courses')

    def get_enrolled_courses(self, obj):
        if obj.role != 'STUDENT':
            return []
        # Return list of course titles the student is enrolled in
        return list(obj.registry_enrollments.values_list('course__title', flat=True))

    def get_taught_courses(self, obj):
        if obj.role != 'INSTRUCTOR':
            return []
        # Return list of course titles the instructor has created
        return list(obj.curated_content.values_list('title', flat=True))

    def create(self, validated_data):
        password = validated_data.pop('password', None)
        if not password:
            raise serializers.ValidationError({"password": "This field is required for creation."})
        
        profile_data = validated_data.pop('profile', {})
        instructor_data = validated_data.pop('instructor_profile', {})
        student_data = validated_data.pop('student_profile', {})

        user = User.objects.create_user(password=password, **validated_data)
        
        # Update profiles
        if profile_data:
            Profile.objects.filter(user=user).update(**profile_data)
        if instructor_data:
            InstructorProfile.objects.filter(user=user).update(**instructor_data)
        if student_data:
            StudentProfile.objects.filter(user=user).update(**student_data)
            
        return user

    def update(self, instance, validated_data):
        password = validated_data.pop('password', None)
        if password:
            instance.set_password(password)
            
        profile_data = validated_data.pop('profile', {})
        instructor_data = validated_data.pop('instructor_profile', {})
        student_data = validated_data.pop('student_profile', {})

        # Update User
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        # Update Profiles
        if profile_data:
            Profile.objects.filter(user=instance).update(**profile_data)
        if instructor_data:
            InstructorProfile.objects.filter(user=instance).update(**instructor_data)
        if student_data:
            StudentProfile.objects.filter(user=instance).update(**student_data)

        return instance
