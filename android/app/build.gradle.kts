plugins {
    id("com.android.application")
    id("org.jetbrains.kotlin.android")
}

android {
    namespace = "com.capstone.fl"
    compileSdk = 34

    defaultConfig {
        applicationId = "com.capstone.fl"
        minSdk = 26
        targetSdk = 34
        versionCode = 3
        versionName = "0.3.0"
        // central server URL is read at runtime, so swapping the server is just
        // a settings change (no rebuild required). The value below is only the
        // initial default.
        buildConfigField("String", "DEFAULT_SERVER_URL", "\"https://kunsan-fl.loca.lt\"")
    }

    buildFeatures { buildConfig = true; viewBinding = true }
    compileOptions { sourceCompatibility = JavaVersion.VERSION_17; targetCompatibility = JavaVersion.VERSION_17 }
    kotlinOptions { jvmTarget = "17" }
}

dependencies {
    implementation("androidx.core:core-ktx:1.13.1")
    implementation("androidx.appcompat:appcompat:1.7.0")
    implementation("com.google.android.material:material:1.12.0")
    implementation("androidx.constraintlayout:constraintlayout:2.1.4")
    implementation("androidx.security:security-crypto:1.1.0-alpha06")
    implementation("com.squareup.okhttp3:okhttp:4.12.0")
    implementation("org.json:json:20240303")
    // Gboard-style background scheduling: only trains when charging + idle + WiFi.
    implementation("androidx.work:work-runtime-ktx:2.9.1")
    // UI polling loop in MainActivity needs the Android dispatcher.
    implementation("org.jetbrains.kotlinx:kotlinx-coroutines-android:1.8.1")
}
