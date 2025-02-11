plugins {
    id("com.android.application")
    id("kotlin-android")
    id("com.google.devtools.ksp")
    id("kotlin-parcelize")
    id("dagger.hilt.android.plugin")
}

android {
    namespace = "net.phbwt.paperwork"
    compileSdk = 34
    buildToolsVersion = "34.0.0"

    defaultConfig {
        applicationId = "net.phbwt.paperwork"
        minSdk = 24
        targetSdk = 34
        versionCode = 1001007
        versionName = "1.1.7"

        resourceConfigurations += arrayOf("en", "fr")

        testInstrumentationRunner = "androidx.test.runner.AndroidJUnitRunner"

        vectorDrawables {
            useSupportLibrary = true
        }

        setProperty("archivesBaseName", "${applicationId}_${versionName}")
    }

    signingConfigs {
        create("release") {
            storeFile = file(File(System.getenv("ANDROID_KEYSTORE") ?: ""))
            storePassword = System.getenv("ANDROID_PASSWORD")
            keyAlias = "OpenPaperView"
            keyPassword = System.getenv("ANDROID_PASSWORD")
        }
    }

    buildTypes {
        release {
            signingConfig = signingConfigs.getByName("release")
            isMinifyEnabled = true
            isShrinkResources = true
            vcsInfo.include  = false
            proguardFiles(
                getDefaultProguardFile("proguard-android-optimize.txt"),
                "proguard-rules.pro"
            )
        }
    }

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }

    kotlinOptions {
        jvmTarget = "17"
    }

    buildFeatures {
        compose = true
        buildConfig = true
    }

    ksp {
        arg("room.schemaLocation", "$projectDir/schemas")
        arg("room.generateKotlin", "true")
    }

    composeOptions {
        // https://developer.android.com/jetpack/androidx/releases/compose-kotlin
        kotlinCompilerExtensionVersion = "1.5.11"
    }

    packaging {
        resources {
            excludes += "/META-INF/{AL2.0,LGPL2.1}"
        }
    }
}

dependencies {

    // https://developer.android.com/jetpack/androidx/versions
    implementation("androidx.activity:activity-compose:1.8.2")
    implementation("androidx.core:core-ktx:1.12.0")
    implementation("androidx.core:core-splashscreen:1.0.1")
    implementation("androidx.datastore:datastore-preferences:1.0.0")

    // kotlinx
    // https://github.com/Kotlin/kotlinx.collections.immutable/blob/master/CHANGELOG.md
    implementation("org.jetbrains.kotlinx:kotlinx-collections-immutable-jvm:0.3.7")

    // Saved state module for ViewModel
    // https://developer.android.com/jetpack/androidx/releases/lifecycle#groovy
    implementation("androidx.lifecycle:lifecycle-runtime-compose:${Versions.lifecycle}")
    implementation("androidx.lifecycle:lifecycle-viewmodel-ktx:${Versions.lifecycle}")
    implementation("androidx.lifecycle:lifecycle-viewmodel-compose:${Versions.lifecycle}")
    implementation("androidx.lifecycle:lifecycle-runtime-ktx:${Versions.lifecycle}")
    implementation("androidx.lifecycle:lifecycle-viewmodel-savedstate:${Versions.lifecycle}")

    // compose
    // https://developer.android.com/jetpack/compose/bom/bom-mapping
    implementation(platform("androidx.compose:compose-bom:2024.04.00"))
//    api(platform("dev.chrisbanes.compose:compose-bom:2023.02.00-beta01"))

    implementation("androidx.compose.ui:ui-tooling-preview")
    debugImplementation("androidx.compose.ui:ui-tooling")
    implementation("androidx.compose.ui:ui")
    implementation("androidx.compose.material3:material3")
    implementation("androidx.compose.material:material-icons-extended")
    androidTestImplementation("androidx.compose.ui:ui-test-junit4")

    // navigation
    implementation("androidx.navigation:navigation-compose:${Versions.navigation}")
    implementation("androidx.hilt:hilt-navigation-compose:${Versions.hiltNavigationCompose}")

    // https://github.com/coil-kt/coil/blob/main/CHANGELOG.md
    implementation("io.coil-kt:coil-compose:2.6.0")

    // Compose Destinations
    implementation("io.github.raamcosta.compose-destinations:core:${Versions.compose_destinations}")
    ksp("io.github.raamcosta.compose-destinations:ksp:${Versions.compose_destinations}")

    // room
    implementation("androidx.room:room-runtime:${Versions.room}")
    ksp("androidx.room:room-compiler:${Versions.room}")
    implementation("androidx.room:room-ktx:${Versions.room}")

    // hilt
    implementation("com.google.dagger:hilt-android:${Versions.hiltDagger}")
    // both hilt-compiler are required
    // cf https://github.com/google/dagger/issues/4058#issuecomment-1739045490
    ksp("com.google.dagger:hilt-compiler:${Versions.hiltDagger}")
    ksp("androidx.hilt:hilt-compiler:${Versions.hiltBase}")

    // OkHttp
    // https://github.com/square/okhttp/blob/master/docs/changelogs/changelog_4x.md
    implementation(platform("com.squareup.okhttp3:okhttp-bom:4.12.0"))
    implementation("com.squareup.okhttp3:okhttp")
    implementation("com.squareup.okhttp3:okhttp-tls")
    implementation("com.squareup.okhttp3:logging-interceptor")

    // workmanager + hilt and coroutine integration
    implementation("androidx.work:work-runtime-ktx:2.9.0")
    implementation("androidx.hilt:hilt-work:${Versions.hiltBase}")
    // https://github.com/gildor/kotlin-coroutines-okhttp/blob/master/CHANGELOG.md
    implementation("ru.gildor.coroutines:kotlin-coroutines-okhttp:1.0")

    testImplementation("junit:junit:4.13.2")
    androidTestImplementation("androidx.test.ext:junit:1.1.5")
    androidTestImplementation("androidx.test.espresso:espresso-core:3.5.1")
    androidTestImplementation("androidx.compose.ui:ui-test-junit4")
}