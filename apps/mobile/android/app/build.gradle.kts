import java.util.Properties

plugins {
    id("com.android.application")
    // The Flutter Gradle Plugin must be applied after the Android and Kotlin Gradle plugins.
    id("dev.flutter.flutter-gradle-plugin")
}

android {
    namespace = "in.priveo.app"
    compileSdk = flutter.compileSdkVersion
    ndkVersion = flutter.ndkVersion

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }

    defaultConfig {
        applicationId = "in.priveo.app"
        // You can update the following values to match your application needs.
        // For more information, see: https://flutter.dev/to/review-gradle-config.
        minSdk = flutter.minSdkVersion
        targetSdk = flutter.targetSdkVersion
        versionCode = flutter.versionCode
        versionName = flutter.versionName
    }

    // dev and prod install side by side. Pick one with --flavor; the default
    // is set in pubspec.yaml. The manifest reads the label from appLabel.
    flavorDimensions += "env"
    productFlavors {
        create("dev") {
            dimension = "env"
            applicationIdSuffix = ".dev"
            manifestPlaceholders["appLabel"] = "Priveo Test"
        }
        create("prod") {
            dimension = "env"
            manifestPlaceholders["appLabel"] = "Priveo"
        }
    }

    // Upload key. key.properties is written by CI from GitHub secrets and is
    // never committed. Without it, release builds fall back to the debug key.
    val keyProps = Properties()
    val keyFile = rootProject.file("key.properties")
    if (keyFile.exists()) keyFile.inputStream().use { keyProps.load(it) }

    signingConfigs {
        if (keyFile.exists()) {
            create("upload") {
                keyAlias = keyProps["keyAlias"] as String
                keyPassword = keyProps["keyPassword"] as String
                storeFile = file(keyProps["storeFile"] as String)
                storePassword = keyProps["storePassword"] as String
            }
        }
    }

    buildTypes {
        release {
            signingConfig = if (keyFile.exists()) signingConfigs.getByName("upload")
            else signingConfigs.getByName("debug")
        }
    }
}

kotlin {
    compilerOptions {
        jvmTarget = org.jetbrains.kotlin.gradle.dsl.JvmTarget.JVM_17
    }
}

flutter {
    source = "../.."
}
