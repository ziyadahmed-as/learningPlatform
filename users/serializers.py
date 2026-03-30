from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password

User = get_user_model()

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = (
            'id', 'username', 'email', 'role', 'bio', 'profile_picture', 
            'first_name', 'last_name', 'expertise', 'education_level', 
            'years_of_experience', 'linkedin', 'portfolio', 
            'proposed_courses', 'cv_file', 'points', 'signal_strength', 'peer_ranking'
        )
        read_only_fields = ('id', 'role', 'signal_strength', 'peer_ranking')

    signal_strength = serializers.SerializerMethodField()
    peer_ranking = serializers.SerializerMethodField()

    def get_signal_strength(self, obj):
        return "100%" if obj.is_active else "0%"

    def get_peer_ranking(self, obj):
        total_users = User.objects.count()
        if total_users <= 1:
            return "TOP 1%"
        better_users = User.objects.filter(points__gt=obj.points).count()
        rank_percent = int((better_users / total_users) * 100)
        if rank_percent < 1: return "TOP 1%"
        return f"TOP {rank_percent}%"

class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=True, validators=[validate_password])
    password_confirm = serializers.CharField(write_only=True, required=True)

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
        validated_data.pop('password_confirm')
        user = User.objects.create_user(
            username=validated_data['username'],
            email=validated_data['email'],
            password=validated_data['password'],
            role=validated_data.get('role', User.Role.STUDENT),
            first_name=validated_data.get('first_name', ''),
            last_name=validated_data.get('last_name', ''),
            expertise=validated_data.get('expertise', ''),
            education_level=validated_data.get('education_level', ''),
            years_of_experience=validated_data.get('years_of_experience', 0),
            bio=validated_data.get('bio', ''),
            linkedin=validated_data.get('linkedin', ''),
            portfolio=validated_data.get('portfolio', ''),
            proposed_courses=validated_data.get('proposed_courses', ''),
            cv_file=validated_data.get('cv_file', None)
        )
        return user

class AdminUserSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=False, validators=[validate_password])

    class Meta:
        model = User
        fields = (
            'id', 'username', 'email', 'password', 'role', 'bio', 
            'profile_picture', 'first_name', 'last_name', 'expertise', 
            'education_level', 'years_of_experience', 'linkedin', 
            'portfolio', 'proposed_courses', 'cv_file', 'points'
        )
        read_only_fields = ('id',)

    def create(self, validated_data):
        password = validated_data.pop('password', None)
        if not password:
            raise serializers.ValidationError({"password": "This field is required for creation."})
        user = User.objects.create_user(password=password, **validated_data)
        return user

    def update(self, instance, validated_data):
        password = validated_data.pop('password', None)
        if password:
            instance.set_password(password)
        return super().update(instance, validated_data)
