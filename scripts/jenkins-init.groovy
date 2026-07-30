// =============================================================================
// Jenkins Init Script — HRMS CI/CD Setup
// Location: <JENKINS_HOME>/init.groovy.d/hrms-init.groovy
//           OR paste this into: Manage Jenkins → Script Console
//
// This script:
//   1. Installs required plugins
//   2. Creates GitHub credentials
//   3. Creates a secret-text credential for NEXT_PUBLIC_API_URL
//   4. Configures GitHub server integration
//
// ⚠️  SECURITY WARNING:
//   Replace placeholder passwords/tokens below with real values.
//   Do NOT commit this file with real credentials to any repository.
// =============================================================================

import jenkins.model.*
import hudson.model.*
import com.cloudbees.plugins.credentials.*
import com.cloudbees.plugins.credentials.common.*
import com.cloudbees.plugins.credentials.domains.*
import com.cloudbees.plugins.credentials.impl.*
import org.jenkinsci.plugins.plaincredentials.impl.*
import hudson.util.Secret
import jenkins.model.Jenkins

// ─── 1. Install Required Plugins ─────────────────────────────────────────────
def pluginsToInstall = [
    'git',                          // Git SCM integration
    'github',                       // GitHub integration & webhooks
    'github-branch-source',         // GitHub branch source for pipelines
    'workflow-aggregator',          // Pipeline plugin (suite)
    'pipeline-stage-view',          // Pipeline stage visualization
    'credentials-binding',          // Credentials binding in pipelines
    'ssh-agent',                    // SSH agent for deployments
    'docker-workflow',              // Docker Pipeline plugin
    'docker-plugin',                // Docker plugin
    'timestamper',                  // Add timestamps to console output
    'ansicolor',                    // ANSI color in console output
    'build-timeout',                // Build timeout configuration
    'ws-cleanup',                   // Workspace cleanup (cleanWs())
    'blueocean',                    // Blue Ocean UI (optional but recommended)
]

def jenkins = Jenkins.instance
def pluginManager = jenkins.pluginManager
def updateCenter = jenkins.updateCenter

println "=== Checking plugins... ==="
updateCenter.updateAllSites()

def installFutures = []
pluginsToInstall.each { pluginName ->
    if (!pluginManager.getPlugin(pluginName)) {
        println "Installing plugin: ${pluginName}"
        def plugin = updateCenter.getPlugin(pluginName)
        if (plugin) {
            installFutures << plugin.deploy(true)
        } else {
            println "⚠️  Plugin not found in update center: ${pluginName}"
        }
    } else {
        println "✓ Already installed: ${pluginName}"
    }
}

if (installFutures) {
    println "Waiting for plugin installations..."
    installFutures.each { it.get() }
    println "✅ All plugins installed — Jenkins restart required"
    jenkins.restart()
}

// ─── 2. Create Credentials ────────────────────────────────────────────────────
println "\n=== Creating Jenkins Credentials... ==="

def credentialsStore = SystemCredentialsProvider.instance.store
def domain = Domain.global()

// Helper: add credential only if it doesn't already exist
def addCredential = { credential ->
    def existing = CredentialsProvider.lookupCredentials(
        Credentials.class,
        Jenkins.instance,
        null,
        null
    ).find { it.id == credential.id }

    if (existing) {
        println "✓ Credential already exists: ${credential.id}"
    } else {
        credentialsStore.addCredentials(domain, credential)
        println "✅ Created credential: ${credential.id}"
    }
}

// ── 2a. GitHub Username/Password credential ───────────────────────────────────
// Replace GITHUB_USERNAME and GITHUB_TOKEN with your actual GitHub credentials
// Use a GitHub Personal Access Token (PAT) as the password for better security
addCredential(new UsernamePasswordCredentialsImpl(
    CredentialsScope.GLOBAL,
    'github-credentials',                       // ← used in Jenkinsfile
    'GitHub Access Credentials',
    'GITHUB_USERNAME',                          // ← replace with your GitHub username
    'GITHUB_TOKEN_OR_PASSWORD'                  // ← replace with GitHub PAT
))

// ── 2b. NEXT_PUBLIC_API_URL secret text ──────────────────────────────────────
addCredential(new StringCredentialsImpl(
    CredentialsScope.GLOBAL,
    'NEXT_PUBLIC_API_URL',                      // ← used in frontend Jenkinsfile
    'Frontend API URL for Next.js build',
    Secret.fromString('http://192.168.1.60:10016')  // ← update if needed
))

// ── 2c. Backend env file (Secret File) ───────────────────────────────────────
// For the Secret File credential (hrms-backend-env), you MUST add it manually:
// Jenkins → Manage Jenkins → Credentials → Add → Secret File
// Upload the /etc/hrms/backend.env file with ID: hrms-backend-env
println ""
println "⚠️  MANUAL STEP REQUIRED:"
println "   Add a 'Secret File' credential with ID: hrms-backend-env"
println "   File content: copy from /etc/hrms/backend.env on the server"
println "   Path: Jenkins → Manage Jenkins → Credentials → Global → Add Credentials"

// ─── 3. Summary ──────────────────────────────────────────────────────────────
println """
\n╔══════════════════════════════════════════════════════╗
║  Jenkins Init Script — DONE                         ║
╠══════════════════════════════════════════════════════╣
║  Credentials created:                               ║
║    ✅ github-credentials (Username/Password)         ║
║    ✅ NEXT_PUBLIC_API_URL (Secret Text)              ║
║    ⚠️  hrms-backend-env (Add manually as Secret File) ║
╠══════════════════════════════════════════════════════╣
║  NEXT: Create Pipeline jobs — see CICD_SETUP_GUIDE  ║
╚══════════════════════════════════════════════════════╝
"""
