from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from .models import Profile, InstructorProfile, StudentProfile

User = get_user_model()

class UserSerializer(serializers.ModelSerializer):
    signal_strength = serializers.SerializerMethodField()
    peer_ranking = serializers.SerializerMethodField()

    # Fields sourced from related Profile model
    bio = serializers.SerializerMethodField()
    profile_picture = serializers.SerializerMethodField()

    # Fields sourced from related InstructorProfile model
    expertise = serializers.SerializerMethodField()
    education_level = serializers.SerializerMethodField()
    years_of_experience = serializers.SerializerMethodField()
    website = serializers.SerializerMethodField()
    portfolio = serializers.SerializerMethodField()
    proposed_courses = serializers.SerializerMethodField()
    cv_file = serializers.SerializerMethodField()
    is_approved_instructor = serializers.SerializerMethodField()

    # Fields sourced from related StudentProfile model
    points = serializers.SerializerMethodField()

    def get_signal_strength(self, obj):
        return "100%" if obj.is_active else "0%"

    def get_peer_ranking(self, obj):
        total_users = User.objects.count()
        if total_users <= 1:
            return "TOP 1%"
        try:
            points = obj.student_profile.points
        except Exception:
            points = 0
        better_users = User.objects.filter(student_profile__points__gt=points).count()
        rank_percent = int((better_users / total_users) * 100)
        if rank_percent < 1:
            return "TOP 1%"
        return f"TOP {rank_percent}%"

    def get_bio(self, obj):
        try:
            return obj.profile.bio or ""
        except Exception:
            return ""

    def get_profile_picture(self, obj):
        try:
            pic = obj.profile.profile_picture
            if pic:
                request = self.context.get('request')
                if request:
                    return request.build_absolute_uri(pic.url)
                return pic.url
            return None
        except Exception:
            return None

    def get_expertise(self, obj):
        try:
            return obj.instructor_profile.expertise or ""
        except Exception:
            return ""

    def get_education_level(self, obj):
        try:
            return obj.instructor_profile.education_level or ""
        except Exception:
            return ""

    def get_years_of_experience(self, obj):
        try:
            return obj.instructor_profile.years_of_experience
        except Exception:
            return 0

    def get_website(self, obj):
        try:
            return obj.instructor_profile.website or ""
        except Exception:
            return ""

    def get_portfolio(self, obj):
        try:
            return obj.instructor_profile.portfolio or ""
        except Exception:
            return ""

    def get_proposed_courses(self, obj):
        try:
            return obj.instructor_profile.proposed_courses or ""
        except Exception:
            return ""

    def get_cv_file(self, obj):
        try:
            cv = obj.instructor_profile.cv_file
            if cv:
                request = self.context.get('request')
                if request:
                    return request.build_absolute_uri(cv.url)
                return cv.url
            return None
        except Exception:
            return None

    def get_is_approved_instructor(self, obj):
        try:
            return obj.instructor_profile.is_approved_instructor
        except Exception:
            return False

    def get_points(self, obj):
        try:
            return obj.student_profile.points
        except Exception:
            return 0

    class Meta:
        model = User
        fields = (
            'id', 'username', 'email', 'role', 'is_superuser', 'bio', 'profile_picture',
            'first_name', 'last_name', 'expertise', 'education_level',
            'years_of_experience', 'website', 'portfolio',
            'proposed_courses', 'cv_file', 'is_approved_instructor', 'points', 
            'signal_strength', 'peer_ranking', 'last_login', 'date_joined'
        )
        read_only_fields = ('id', 'role', 'is_superuser', 'is_approved_instructor', 'signal_strength', 'peer_ranking', 'last_login', 'date_joined')

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
    # Using CharField instead of URLField so blank strings from multipart/form-data
    # don't trigger URL validation errors when the field is left empty.
    website = serializers.CharField(required=False, allow_blank=True)
    portfolio = serializers.CharField(required=False, allow_blank=True)
    proposed_courses = serializers.CharField(required=False, allow_blank=True)
    cv_file = serializers.FileField(required=False, allow_null=True)

    class Meta:
        model = User
        fields = ('username', 'email', 'password', 'password_confirm', 'first_name', 'last_name',
                  'role',  # ← must be included so the chosen role (INSTRUCTOR/STUDENT) is persisted
                  'expertise', 'education_level', 'years_of_experience', 'bio', 
                  'website', 'portfolio', 'proposed_courses', 'cv_file')

    def validate_username(self, value):
        if User.objects.filter(username__iexact=value).exists():
            raise serializers.ValidationError("A user with this username already exists.")
        return value

    def validate_email(self, value):
        if not value:
            raise serializers.ValidationError("Email is required.")
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError("A user with this email address already exists.")
        return value.lower()

    def validate(self, attrs):
        if attrs['password'] != attrs['password_confirm']:
            raise serializers.ValidationError({"password": "Password fields didn't match."})
        return attrs

    def create(self, validated_data):
        password = validated_data.pop('password')
        validated_data.pop('password_confirm')
        role = validated_data.get('role', 'STUDENT')
        
        # Extract profile/instructor data before user creation
        bio = validated_data.pop('bio', '')
        expertise = validated_data.pop('expertise', '')
        education_level = validated_data.pop('education_level', '')
        years_of_experience = validated_data.pop('years_of_experience', 0)
        website = validated_data.pop('website', '')
        portfolio = validated_data.pop('portfolio', '')
        proposed_courses = validated_data.pop('proposed_courses', '')
        cv_file = validated_data.pop('cv_file', None)

        user = User.objects.create_user(
            password=password,
            **validated_data
        )
        
        # Update base profile (bio) for all users
        profile = user.profile
        profile.bio = bio
        profile.save()
        
        # Only populate instructor-specific profile fields when registering as INSTRUCTOR
        if role == 'INSTRUCTOR':
            instr_profile = user.instructor_profile
            instr_profile.expertise = expertise
            instr_profile.education_level = education_level
            instr_profile.years_of_experience = years_of_experience
            instr_profile.website = website or ''
            instr_profile.portfolio = portfolio or ''
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
            # Handle cases where multiple users might share an email
            user = User.objects.filter(email=username_or_email).first()
            if user:
                # If found, set the 'username' to the actual username for the standard auth logic
                attrs['username'] = user.username
                
        data = super().validate(attrs)
        # Add user data to response
        data['user'] = UserSerializer(self.user).data
        return data

class AdminUserSerializer(serializers.ModelSerializer):
    # No validate_password validator here — we do it manually in validate()
    # so that an empty string (on update = "don't change") doesn't trigger it.
    password = serializers.CharField(write_only=True, required=False, allow_blank=True)
    
    # Writable fields for admin
    first_name = serializers.CharField(required=False, allow_blank=True)
    last_name = serializers.CharField(required=False, allow_blank=True)
    
    bio = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    profile_picture = serializers.SerializerMethodField()
    expertise = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    education_level = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    years_of_experience = serializers.IntegerField(required=False, allow_null=True)
    cv_file = serializers.SerializerMethodField()
    website = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    portfolio = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    proposed_courses = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    is_approved_instructor = serializers.BooleanField(required=False, allow_null=True)
    points = serializers.IntegerField(required=False, allow_null=True)
    
    enrolled_courses = serializers.SerializerMethodField()
    taught_courses = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = (
            'id', 'username', 'email', 'password', 'role', 'bio', 
            'profile_picture', 'first_name', 'last_name', 'expertise', 
            'education_level', 'years_of_experience', 'website', 
            'portfolio', 'proposed_courses', 'cv_file', 'is_approved_instructor', 'points',
            'enrolled_courses', 'taught_courses'
        )
        read_only_fields = ('id', 'enrolled_courses', 'taught_courses')

    def get_enrolled_courses(self, obj):
        if obj.role != 'STUDENT':
            return []
        try:
            return list(obj.registry_enrollments.values_list('course__title', flat=True))
        except Exception:
            return []

    def get_taught_courses(self, obj):
        if obj.role != 'INSTRUCTOR':
            return []
        try:
            return list(obj.curated_content.values_list('title', flat=True))
        except Exception:
            return []

    def get_profile_picture(self, obj):
        try:
            pic = obj.profile.profile_picture
            if pic:
                request = self.context.get('request')
                if request:
                    return request.build_absolute_uri(pic.url)
                return pic.url
            return None
        except Exception:
            return None

    def get_cv_file(self, obj):
        try:
            cv = obj.instructor_profile.cv_file
            if cv:
                request = self.context.get('request')
                if request:
                    return request.build_absolute_uri(cv.url)
                return cv.url
            return None
        except Exception:
            return None

    def validate_username(self, value):
        instance = self.instance  # None on create, User obj on update
        qs = User.objects.filter(username__iexact=value)
        if instance:
            qs = qs.exclude(pk=instance.pk)
        if qs.exists():
            raise serializers.ValidationError("A user with this username already exists.")
        return value

    def validate_email(self, value):
        # Email is required on create but optional on update
        if not value and not self.instance:
            raise serializers.ValidationError("Email is required.")
        if value:
            instance = self.instance
            qs = User.objects.filter(email__iexact=value)
            if instance:
                qs = qs.exclude(pk=instance.pk)
            if qs.exists():
                raise serializers.ValidationError("A user with this email address already exists.")
            return value.lower()
        return value

    def validate(self, attrs):
        password = attrs.get('password', '')
        # On create, password is required
        if not self.instance and not password:
            raise serializers.ValidationError({"password": "Password is required when creating a user."})
        # If a password is provided (create or update), validate its strength
        if password:
            from django.contrib.auth.password_validation import validate_password as _vp
            from django.core.exceptions import ValidationError as DjValidationError
            try:
                _vp(password)
            except DjValidationError as e:
                raise serializers.ValidationError({"password": list(e.messages)})
        return attrs

    def create(self, validated_data):
        password = validated_data.pop('password')
        
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
            
        # Extract profile fields
        bio = validated_data.pop('bio', None)
        expertise = validated_data.pop('expertise', None)
        education_level = validated_data.pop('education_level', None)
        years_of_experience = validated_data.pop('years_of_experience', None)
        website = validated_data.pop('website', None)
        portfolio = validated_data.pop('portfolio', None)
        proposed_courses = validated_data.pop('proposed_courses', None)
        cv_file = validated_data.pop('cv_file', None)
        is_approved_instructor = validated_data.pop('is_approved_instructor', None)
        points = validated_data.pop('points', None)

        # Update User
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        # Update Profiles
        if bio is not None:
            Profile.objects.filter(user=instance).update(bio=bio)
        
        # Instructor Profile
        instr_updates = {}
        if expertise is not None: instr_updates['expertise'] = expertise
        if education_level is not None: instr_updates['education_level'] = education_level
        if years_of_experience is not None: instr_updates['years_of_experience'] = years_of_experience
        if website is not None: instr_updates['website'] = website
        if portfolio is not None: instr_updates['portfolio'] = portfolio
        if proposed_courses is not None: instr_updates['proposed_courses'] = proposed_courses
        if cv_file is not None: instr_updates['cv_file'] = cv_file
        if is_approved_instructor is not None: instr_updates['is_approved_instructor'] = is_approved_instructor
        
        if instr_updates:
            InstructorProfile.objects.filter(user=instance).update(**instr_updates)

        # Student Profile
        if points is not None:
            StudentProfile.objects.filter(user=instance).update(points=points)

        return instance
