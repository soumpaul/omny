class UserModel {
  final int id;
  final String email;
  final String firebaseUid;
  final String displayName;
  final String phoneNumber;
  final String profilePicture;
  final String householdRole;
  final int? householdId;
  final bool isPatient;
  final bool isCaregiver;
  final bool isPrimaryCaregiver;
  final DateTime? dateJoined;
  final DateTime? lastLogin;

  UserModel({
    required this.id,
    required this.email,
    required this.firebaseUid,
    required this.displayName,
    required this.phoneNumber,
    required this.profilePicture,
    required this.householdRole,
    this.householdId,
    required this.isPatient,
    required this.isCaregiver,
    required this.isPrimaryCaregiver,
    this.dateJoined,
    this.lastLogin,
  });

  factory UserModel.fromJson(Map<String, dynamic> json) {
    return UserModel(
      id: json['id'] as int,
      email: json['email'] as String,
      firebaseUid: json['firebase_uid'] as String,
      displayName: json['display_name'] as String? ?? '',
      phoneNumber: json['phone_number'] as String? ?? '',
      profilePicture: json['profile_picture'] as String? ?? '',
      householdRole: json['household_role'] as String? ?? 'caregiver',
      householdId: json['household_id'] as int?,
      isPatient: json['is_patient'] as bool? ?? false,
      isCaregiver: json['is_caregiver'] as bool? ?? false,
      isPrimaryCaregiver: json['is_primary_caregiver'] as bool? ?? false,
      dateJoined: json['date_joined'] != null
          ? DateTime.parse(json['date_joined'] as String)
          : null,
      lastLogin: json['last_login'] != null
          ? DateTime.parse(json['last_login'] as String)
          : null,
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'email': email,
      'firebase_uid': firebaseUid,
      'display_name': displayName,
      'phone_number': phoneNumber,
      'profile_picture': profilePicture,
      'household_role': householdRole,
      'household_id': householdId,
      'is_patient': isPatient,
      'is_caregiver': isCaregiver,
      'is_primary_caregiver': isPrimaryCaregiver,
      'date_joined': dateJoined?.toIso8601String(),
      'last_login': lastLogin?.toIso8601String(),
    };
  }

  UserModel copyWith({
    int? id,
    String? email,
    String? firebaseUid,
    String? displayName,
    String? phoneNumber,
    String? profilePicture,
    String? householdRole,
    int? householdId,
    bool? isPatient,
    bool? isCaregiver,
    bool? isPrimaryCaregiver,
    DateTime? dateJoined,
    DateTime? lastLogin,
  }) {
    return UserModel(
      id: id ?? this.id,
      email: email ?? this.email,
      firebaseUid: firebaseUid ?? this.firebaseUid,
      displayName: displayName ?? this.displayName,
      phoneNumber: phoneNumber ?? this.phoneNumber,
      profilePicture: profilePicture ?? this.profilePicture,
      householdRole: householdRole ?? this.householdRole,
      householdId: householdId ?? this.householdId,
      isPatient: isPatient ?? this.isPatient,
      isCaregiver: isCaregiver ?? this.isCaregiver,
      isPrimaryCaregiver: isPrimaryCaregiver ?? this.isPrimaryCaregiver,
      dateJoined: dateJoined ?? this.dateJoined,
      lastLogin: lastLogin ?? this.lastLogin,
    );
  }
}
