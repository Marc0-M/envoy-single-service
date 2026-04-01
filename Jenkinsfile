import groovy.json.JsonOutput
import groovy.json.JsonSlurperClassic


def microserviceCatalog = [
  'annuity-services': [
    [microserviceName: 'annuity-agent-api', serviceName: 'service-annuity-agent-api', pathPrefix: '/annuity-agent-api'],
    [microserviceName: 'annuity-contract-entity-api', serviceName: 'service-annuity-contract-entity-api', pathPrefix: '/annuity-contract-entity-api'],
    [microserviceName: 'annuity-contract-financial-api', serviceName: 'service-annuity-contract-financial-api', pathPrefix: '/annuity-contract-financial-api'],
    [microserviceName: 'annuity-contract-info-api', serviceName: 'service-annuity-contract-info-api', pathPrefix: '/annuity-contract-info-api'],
    [microserviceName: 'annuity-entity-api', serviceName: 'service-annuity-entity-api', pathPrefix: '/annuity-entity-api'],
    [microserviceName: 'annuity-utility-services', serviceName: 'service-annuity-utility-services', pathPrefix: '/annuity-utility-services'],
    [microserviceName: 'annuity-webtransdb-api', serviceName: 'service-annuity-webtransdb-api', pathPrefix: '/annuity-webtransdb-api'],
  ],
  'digtran-services': [
    [microserviceName: 'admin-common-services', serviceName: 'service-admin-common-services', pathPrefix: '/admin-common-services'],
    [microserviceName: 'claims-services', serviceName: 'service-claims-services', pathPrefix: '/claims-services'],
    [microserviceName: 'customer-entity-services', serviceName: 'service-customer-entity-services', pathPrefix: '/customer-entity-services'],
    [microserviceName: 'newgen-services', serviceName: 'service-newgen-services', pathPrefix: '/newgen-services'],
    [microserviceName: 'tax-services', serviceName: 'service-tax-services', pathPrefix: '/tax-services'],
    [microserviceName: 'transaction-data-services', serviceName: 'service-transaction-data-services', pathPrefix: '/transaction-services'],
    [microserviceName: 'transaction-orchestrator-services', serviceName: 'service-transaction-orchestrator-services', pathPrefix: '/transaction-orchestrator'],
  ],
  'document-services': [
    [microserviceName: 'ultradoc-services', serviceName: 'service-ultradoc-services', pathPrefix: '/ultradoc-services'],
  ],
  'garwin-int-apps': [
    [microserviceName: 'garwin-annuity-admin-app', serviceName: 'service-garwin-annuity-admin-app', pathPrefix: '/grwn-annuity-admin-app'],
    [microserviceName: 'garwin-jmt-app', serviceName: 'service-garwin-jmt-app', pathPrefix: '/grwn-jmt-app'],
    [microserviceName: 'nscc-configurator-app', serviceName: 'service-nscc-configurator-app', pathPrefix: '/nscc-configurator-app'],
    [microserviceName: 'basdashboard', serviceName: 'service-basdashboard', pathPrefix: '/basdashboard'],
  ],
  'garwin-services': [
    [microserviceName: 'garwin-agent-services', serviceName: 'service-garwin-agent-services', pathPrefix: '/grwn-agent-services'],
    [microserviceName: 'garwin-contract-services', serviceName: 'service-garwin-contract-services', pathPrefix: '/grwn-contract-services'],
    [microserviceName: 'garwin-contractentity-services', serviceName: 'service-garwin-contractentity-services', pathPrefix: '/grwn-contractentity-services'],
    [microserviceName: 'garwin-data-services', serviceName: 'service-garwin-data-services', pathPrefix: '/grwn-data-services'],
    [microserviceName: 'garwin-financial-services', serviceName: 'service-garwin-financial-services', pathPrefix: '/grwn-financial-services'],
    [microserviceName: 'garwin-goodorder-service', serviceName: 'service-garwin-goodorder-service', pathPrefix: '/grwn-goodorder-service'],
    [microserviceName: 'garwin-maintenance-services', serviceName: 'service-garwin-maintenance-services', pathPrefix: '/grwn-maint-services'],
    [microserviceName: 'garwin-quote-services', serviceName: 'service-garwin-quote-services', pathPrefix: '/grwn-quote-services'],
    [microserviceName: 'garwin-report-services', serviceName: 'service-garwin-report-services', pathPrefix: '/grwn-report-services'],
    [microserviceName: 'garwin-tranprocess-services', serviceName: 'service-garwin-tranprocess-services', pathPrefix: '/grwn-process-services'],
    [microserviceName: 'garwin-validation-services', serviceName: 'service-garwin-validation-services', pathPrefix: '/grwn-validation-services'],
  ],
  'generic-internal-service': [
    [microserviceName: 'garwin-cadaily-app', serviceName: 'service-garwin-cadaily-app', pathPrefix: '/icadaily'],
    [microserviceName: 'garwin-camonthly-app', serviceName: 'service-garwin-camonthly-app', pathPrefix: '/icamonthly'],
  ],
  'lifecad-services': [
    [microserviceName: 'lifecad-agent-services', serviceName: 'service-lifecad-agent-services', pathPrefix: '/lc-agent-services'],
    [microserviceName: 'lifecad-batchcycle-services', serviceName: 'service-lifecad-batchcycle-services', pathPrefix: '/lc-batchcycle-services'],
    [microserviceName: 'lifecad-contractentity-services', serviceName: 'service-lifecad-contractentity-services', pathPrefix: '/lc-contractentity-services'],
    [microserviceName: 'lifecad-contractinfo-services', serviceName: 'service-lifecad-contractinfo-services', pathPrefix: '/lc-contractinfo-services'],
    [microserviceName: 'lifecad-correspondence-services', serviceName: 'service-lifecad-correspondence-services', pathPrefix: '/lc-correspondence-services'],
    [microserviceName: 'lifecad-data-services', serviceName: 'service-lifecad-data-services', pathPrefix: '/lc-data-services'],
    [microserviceName: 'lifecad-financialtran-services', serviceName: 'service-lifecad-financialtran-services', pathPrefix: '/lc-financialtran-services'],
    [microserviceName: 'lifecad-nonfinancialtran-services', serviceName: 'service-lifecad-nonfinancialtran-services', pathPrefix: '/lc-nonfinancialtran-services'],
  ],
  'portal-services': [
    [microserviceName: 'audit-services', serviceName: 'service-audit-services', pathPrefix: '/audit-services'],
    [microserviceName: 'document-engine', serviceName: 'service-document-engine', pathPrefix: '/document-engine'],
    [microserviceName: 'email-services', serviceName: 'service-email-services', pathPrefix: '/email-services'],
    [microserviceName: 'portal-adminmodule-api', serviceName: 'service-portal-adminmodule-api', pathPrefix: '/portal-adminmodule-api'],
    [microserviceName: 'portal-bobreport-services', serviceName: 'service-portal-bobreport-services', pathPrefix: '/portal-bobreport-services'],
    [microserviceName: 'portal-claims-api', serviceName: 'service-portal-claims-api', pathPrefix: '/portal-claims-api'],
    [microserviceName: 'portal-commission-services', serviceName: 'service-portal-commission-services', pathPrefix: '/portal-commission-services'],
    [microserviceName: 'portal-csr-api', serviceName: 'service-portal-csr-api', pathPrefix: '/portal-csr-api'],
    [microserviceName: 'portal-customer-api', serviceName: 'service-portal-customer-api', pathPrefix: '/portal-customer-api'],
    [microserviceName: 'portal-professional-api', serviceName: 'service-portal-professional-api', pathPrefix: '/portal-professional-api'],
    [microserviceName: 'portal-transaction-api', serviceName: 'service-portal-transaction-api', pathPrefix: '/portal-transaction-api'],
    [microserviceName: 'portal-userprofile-api', serviceName: 'service-portal-userprofile-api', pathPrefix: '/portal-userprofile-api'],
    [microserviceName: 'profile-services', serviceName: 'service-profile-services', pathPrefix: '/profile-services'],
    [microserviceName: 'sharepoint-services', serviceName: 'service-sharepoint-services', pathPrefix: '/sharepoint-services'],
  ],
]

def environmentChoices = [
  'Select_one',
  'dev',
  'devb',
  'devc',
  'intg',
  'intgb',
  'intgc',
  'accp',
  'accpb',
  'accpc',
  'proda',
  'prodb',
]

def catalogJson = JsonOutput.toJson(microserviceCatalog)

def activeChoiceScript(String body) {
  [
    $class: 'GroovyScript',
    fallbackScript: [
      classpath: [],
      sandbox: true,
      script: 'return ["Unable to load values"]',
    ],
    script: [
      classpath: [],
      sandbox: true,
      script: body,
    ],
  ]
}

def splitSelections(def rawValue) {
  if (rawValue == null) {
    return []
  }

  if (rawValue instanceof Collection) {
    return rawValue.collect { it.toString().trim() }.findAll { it }
  }

  String text = rawValue.toString().trim()
  if (!text || text == '[]') {
    return []
  }

  text = text.replace('[', '').replace(']', '')

  return text
    .split(/\s*,\s*|\r?\n/)
    .collect { it.trim() }
    .findAll { it }
}

boolean isProdEnv(String targetEnv) {
  String normalizedEnv = targetEnv?.toLowerCase() ?: ''
  return normalizedEnv ==~ /prod[a-z]*[a-z]?/ || normalizedEnv == 'dr'
}

boolean isAccpEnv(String targetEnv) {
  String normalizedEnv = targetEnv?.toLowerCase() ?: ''
  return normalizedEnv == 'accp' || normalizedEnv.startsWith('accp')
}

boolean isIntgEnv(String targetEnv) {
  String normalizedEnv = targetEnv?.toLowerCase() ?: ''
  return normalizedEnv == 'intg' || normalizedEnv.startsWith('intg')
}

boolean isDevEnv(String targetEnv) {
  String normalizedEnv = targetEnv?.toLowerCase() ?: ''
  return normalizedEnv == 'dev' || normalizedEnv.startsWith('dev')
}

String getRegion(String targetEnv) {
  return (targetEnv?.toLowerCase() == 'dr') ? 'us-west-2' : 'us-east-1'
}

String getKubeConfig(String targetEnv) {
  if (isProdEnv(targetEnv)) {
    return 'prod'
  }
  if (isAccpEnv(targetEnv)) {
    return 'accp'
  }
  if (isIntgEnv(targetEnv)) {
    return 'intg'
  }
  if (isDevEnv(targetEnv)) {
    return 'dev'
  }
  return targetEnv
}

String getAwsEnv(String targetEnv) {
  if (isProdEnv(targetEnv)) {
    return 'prod'
  }
  if (isAccpEnv(targetEnv)) {
    return 'accp'
  }
  if (isIntgEnv(targetEnv)) {
    return 'intg'
  }
  if (isDevEnv(targetEnv)) {
    return 'dev'
  }
  return targetEnv
}

String getCredentialId(String targetEnv) {
  if (isProdEnv(targetEnv)) {
    return 'sa_deploy_prod'
  }
  if (isAccpEnv(targetEnv)) {
    return 'sa_deploy_accp'
  }
  if (isIntgEnv(targetEnv)) {
    return 'sa_deploy_intg'
  }
  if (isDevEnv(targetEnv)) {
    return 'sa_deploy_dev'
  }
  return 'sa_deploy_null'
}

String getBackendCaSecretName(String groupName) {
  String normalizedGroup = groupName?.trim() ?: ''
  List<String> groupParts = normalizedGroup.tokenize('-')
  String groupPrefix = groupParts ? groupParts.first() : normalizedGroup
  return "${groupPrefix}-backend-ca"
}

boolean hasWildcardHostname(String hostname) {
  return (hostname ?: '').contains('*')
}

String shellQuote(String value) {
  return "'${value.replace("'", "'\"'\"'")}'"
}

String sanitizeHelmExtraArgs(String rawValue) {
  String trimmedValue = rawValue?.trim()
  if (!trimmedValue) {
    return ''
  }

  if (
    trimmedValue.contains('\n') ||
    trimmedValue.contains('\r') ||
    trimmedValue.contains(';') ||
    trimmedValue.contains('|') ||
    trimmedValue.contains('&') ||
    trimmedValue.contains('>') ||
    trimmedValue.contains('<') ||
    trimmedValue.contains('`') ||
    trimmedValue.contains('$(') ||
    trimmedValue.contains('${')
  ) {
    throw new IllegalArgumentException('HELM_EXTRA_ARGS contains unsupported shell metacharacters. Use whitespace-separated Helm arguments only.')
  }

  return trimmedValue
    .split(/\s+/)
    .findAll { it }
    .collect { shellQuote(it) }
    .join(' ')
}

List<String> buildCommonHelmArgs(def serviceConfig, def paramsMap, def envMap) {
  List<String> command = [
    shellQuote(envMap.CHART_REF),
    "--version ${shellQuote(paramsMap.CHART_VERSION)}",
    "--set-string microservice=${shellQuote(serviceConfig.microserviceName)}",
    "--set-string group=${shellQuote(paramsMap.GROUP_NAME)}",
    "--set-string env=${shellQuote(paramsMap.ENV)}",
    "--set-string gateway.name=${shellQuote(envMap.GATEWAY_NAME)}",
    "--set-string backend.caSecretName=${shellQuote(envMap.BACKEND_CA_SECRET_NAME)}",
    "--set-string backend.hostname=${shellQuote(envMap.BACKEND_HOSTNAME)}",
    "--set backend.port=${shellQuote(paramsMap.BACKEND_PORT)}",
    "--set backend.tlsEnabled=${paramsMap.BACKEND_TLS_ENABLED}",
    "--set backendTrafficPolicy.create=${paramsMap.CREATE_BACKEND_TRAFFIC_POLICY}",
    "--set-string timeouts.request=${shellQuote(paramsMap.REQUEST_TIMEOUT)}",
    "--set-string pathPrefix=${shellQuote(serviceConfig.pathPrefix)}",
    "--set-string svc=${shellQuote(serviceConfig.serviceName)}",
  ]

  String extraArgs = envMap.HELM_EXTRA_ARGS_SANITIZED?.trim()
  if (extraArgs) {
    command << extraArgs
  }

  return command
}

String buildHelmCommand(def serviceConfig, String releaseName, def paramsMap, def envMap) {
  List<String> command = [
    "helm upgrade --install ${shellQuote(releaseName)}",
    "--kube-context ${shellQuote(envMap.KUBE_CONFIG)}",
  ]
  command.addAll(buildCommonHelmArgs(serviceConfig, paramsMap, envMap))
  return command.join(" \\\n  ")
}

String buildHelmTemplateCommand(def serviceConfig, String releaseName, def paramsMap, def envMap) {
  List<String> command = [
    "helm template ${shellQuote(releaseName)}",
  ]
  command.addAll(buildCommonHelmArgs(serviceConfig, paramsMap, envMap))
  return command.join(" \\\n  ")
}

properties([
  parameters([
    string(
      name: 'NODE_LABEL',
      defaultValue: 'rhel8-eks-deploy-openjdk11-17-hlm',
      description: 'Jenkins agent to host all stages.'
    ),
    [
      $class: 'ChoiceParameter',
      choiceType: 'PT_SINGLE_SELECT',
      description: 'Select the microservice group to deploy.',
      filterLength: 1,
      filterable: true,
      name: 'GROUP_NAME',
      script: activeChoiceScript("""
        import groovy.json.JsonSlurperClassic

        def catalog = new JsonSlurperClassic().parseText('''${catalogJson}''')
        return catalog.keySet().toList().sort()
      """.stripIndent()),
    ],
    choice(
      name: 'ENV',
      choices: environmentChoices.join('\n'),
      description: 'Target environment.'
    ),
    [
      $class: 'CascadeChoiceParameter',
      choiceType: 'PT_MULTI_SELECT',
      description: 'Select one or more microservices from the selected group.',
      filterLength: 1,
      filterable: true,
      name: 'MICROSERVICES',
      referencedParameters: 'GROUP_NAME',
      script: activeChoiceScript("""
        import groovy.json.JsonSlurperClassic

        def catalog = new JsonSlurperClassic().parseText('''${catalogJson}''')
        def groupName = GROUP_NAME ?: ''
        return (catalog[groupName] ?: []).collect { it.microserviceName }
      """.stripIndent()),
    ],
    string(
      name: 'CHART_VERSION',
      defaultValue: '0.1.0',
      description: 'OCI chart version to deploy.'
    ),
    booleanParam(
      name: 'OVERRIDE_GATEWAY_NAME',
      defaultValue: false,
      description: 'Check this only if you need to override the default gateway name convention.'
    ),
    string(
      name: 'CUSTOM_GATEWAY_NAME',
      defaultValue: '',
      description: 'Optional. This value is used only when OVERRIDE_GATEWAY_NAME is checked; otherwise it is ignored.'
    ),
    string(
      name: 'BACKEND_PORT',
      defaultValue: '443',
      description: 'Backend Kubernetes Service port.'
    ),
    booleanParam(
      name: 'BACKEND_TLS_ENABLED',
      defaultValue: true,
      description: 'Create BackendTLSPolicy and validate backend TLS.'
    ),
    booleanParam(
      name: 'CREATE_BACKEND_TRAFFIC_POLICY',
      defaultValue: false,
      description: 'Create BackendTrafficPolicy with cookie-based consistent hash for the selected microservice releases.'
    ),
    string(
      name: 'REQUEST_TIMEOUT',
      defaultValue: '60s',
      description: 'HTTPRoute request timeout passed to the chart. Reduce this per run when a specific microservice needs a shorter upstream timeout.'
    ),
    string(
      name: 'BACKEND_HOSTNAME',
      defaultValue: '',
      description: 'Backend TLS hostname used for SNI/certificate validation. Use a concrete DNS name; wildcards are not supported.'
    ),
    booleanParam(
      name: 'VALIDATE_ONLY',
      defaultValue: false,
      description: 'Render and validate manifests without applying them.'
    ),
    string(
      name: 'HELM_EXTRA_ARGS',
      defaultValue: '',
      description: 'Optional extra Helm CLI arguments appended to each deploy.'
    ),
  ])
])

pipeline {
  agent {
    node {
      label "${params.NODE_LABEL ?: 'rhel8-eks-deploy-openjdk11-17-hlm'}"
    }
  }

  options {
    disableConcurrentBuilds()
    skipDefaultCheckout()
    timestamps()
  }

  environment {
    ARTIFACTORY_HOST = 'artifactory.tools.vaapps.net'
    CHART_REF = 'oci://artifactory.tools.vaapps.net/envoy-single-service/envoy-single-service'
  }

  stages {
    stage('Resolve Selection') {
      steps {
        script {
          def selectedMicroservices = splitSelections(params.MICROSERVICES)
          def groupServices = microserviceCatalog[params.GROUP_NAME]

          if (!params.GROUP_NAME?.trim()) {
            error('GROUP_NAME is required.')
          }
          if (!groupServices) {
            error("Unknown GROUP_NAME '${params.GROUP_NAME}'.")
          }
          if (selectedMicroservices.isEmpty()) {
            error('Select at least one microservice from MICROSERVICES.')
          }
          selectedMicroservices.each { microserviceName ->
            if (!groupServices.find { it.microserviceName == microserviceName }) {
              error("Microservice '${microserviceName}' does not belong to group '${params.GROUP_NAME}'.")
            }
          }

          env.REGION = getRegion(params.ENV)
          env.KUBE_CONFIG = getKubeConfig(params.ENV)
          env.AWS_ENV = getAwsEnv(params.ENV)
          env.CRED_ID = getCredentialId(params.ENV)
          boolean overrideGatewayName = params.OVERRIDE_GATEWAY_NAME
          String defaultGatewayName = "gw-${params.ENV.toLowerCase()}"
          String customGatewayName = params.CUSTOM_GATEWAY_NAME?.trim()
          env.OVERRIDE_GATEWAY_NAME = overrideGatewayName.toString()
          env.GATEWAY_NAME = overrideGatewayName ? customGatewayName : defaultGatewayName
          env.BACKEND_CA_SECRET_NAME = getBackendCaSecretName(params.GROUP_NAME)
          env.BACKEND_HOSTNAME = params.BACKEND_HOSTNAME?.trim() ?: ''
          env.HELM_EXTRA_ARGS_SANITIZED = sanitizeHelmExtraArgs(params.HELM_EXTRA_ARGS)
          env.SELECTED_MICROSERVICES_JSON = JsonOutput.toJson(selectedMicroservices)

          if (env.CRED_ID == 'sa_deploy_null') {
            error("No AWS deployment credential mapping found for environment '${params.ENV}'.")
          }
          if (overrideGatewayName && !env.GATEWAY_NAME) {
            error('CUSTOM_GATEWAY_NAME is required when OVERRIDE_GATEWAY_NAME is enabled.')
          }
          if (params.BACKEND_TLS_ENABLED && !env.BACKEND_HOSTNAME) {
            error('BACKEND_HOSTNAME is required when BACKEND_TLS_ENABLED is enabled. Use a concrete backend DNS name.')
          }
          if (params.BACKEND_TLS_ENABLED && hasWildcardHostname(env.BACKEND_HOSTNAME)) {
            error("BACKEND_HOSTNAME '${env.BACKEND_HOSTNAME}' is invalid for BackendTLSPolicy. Use a concrete DNS name, not a wildcard.")
          }

          currentBuild.displayName = "${params.ENV}-${selectedMicroservices.join('+')}-${params.CHART_VERSION}-#${currentBuild.number}"

          echo "Group: ${params.GROUP_NAME}"
          echo "Environment: ${params.ENV}"
          echo "Region: ${env.REGION}"
          echo "Kube context: ${env.KUBE_CONFIG}"
          echo "Override gateway name: ${env.OVERRIDE_GATEWAY_NAME}"
          echo "Gateway name: ${env.GATEWAY_NAME}"
          echo "AWS credential ID: ${env.CRED_ID}"
          echo "Backend CA secret: ${env.BACKEND_CA_SECRET_NAME}"
          echo "Backend hostname: ${env.BACKEND_HOSTNAME}"
          echo "Create BackendTrafficPolicy: ${params.CREATE_BACKEND_TRAFFIC_POLICY}"
          echo "Request timeout: ${params.REQUEST_TIMEOUT}"
          echo "Selected microservices: ${selectedMicroservices.join(', ')}"
        }
      }
    }

    stage('Validate Selected Charts') {
      steps {
        withCredentials([
          [
            $class: 'AmazonWebServicesCredentialsBinding',
            accessKeyVariable: 'AWS_ACCESS_KEY_ID',
            credentialsId: env.CRED_ID,
            secretKeyVariable: 'AWS_SECRET_ACCESS_KEY'
          ],
          usernamePassword(
            credentialsId: 'f06cf8c1-1b3c-44e0-bc68-35e0f8a1a6fa',
            usernameVariable: 'USERNAME',
            passwordVariable: 'PASSWORD'
          )
        ]) {
          withEnv([
            "AWS_DEFAULT_REGION=${env.REGION}",
            "AWS_REGION=${env.REGION}",
            "ORIGINAL_KUBECONFIG=${env.KUBECONFIG ?: ''}",
            "KUBECONFIG=${env.WORKSPACE}/.kube-validate/config",
            "HELM_CONFIG_HOME=${env.WORKSPACE}/.helm-validate",
            "HELM_CACHE_HOME=${env.WORKSPACE}/.helm-validate/cache",
            "HELM_DATA_HOME=${env.WORKSPACE}/.helm-validate/data",
            "HELM_REGISTRY_CONFIG=${env.WORKSPACE}/.helm-validate/registry/config.json",
            "HELM_EXPERIMENTAL_OCI=1"
          ]) {
            sh '''
              set +x
              mkdir -p "$(dirname "$KUBECONFIG")"
              mkdir -p "$HELM_CONFIG_HOME/registry" "$HELM_CACHE_HOME" "$HELM_DATA_HOME"
              if [ -n "$ORIGINAL_KUBECONFIG" ]; then
                KUBECONFIG="$ORIGINAL_KUBECONFIG" kubectl config view --raw > "$KUBECONFIG"
              else
                env -u KUBECONFIG kubectl config view --raw > "$KUBECONFIG"
              fi
              sed -i 's#client.authentication.k8s.io/v1alpha1#client.authentication.k8s.io/v1beta1#g' "$KUBECONFIG"
              printf '%s' "$PASSWORD" | helm registry login "$ARTIFACTORY_HOST" \
                --username "$USERNAME" \
                --password-stdin
              set -x

              helm pull "$CHART_REF" --version "$CHART_VERSION" --debug

              helm show chart "$CHART_REF" --version "$CHART_VERSION"
            '''

            script {
              def selectedMicroservices = new JsonSlurperClassic().parseText(env.SELECTED_MICROSERVICES_JSON)

              selectedMicroservices.each { microserviceName ->
                def serviceConfig = microserviceCatalog[params.GROUP_NAME].find { it.microserviceName == microserviceName }
                def releaseName = "${microserviceName}-${params.ENV}"
                def helmTemplateCommand = this.buildHelmTemplateCommand(serviceConfig, releaseName, params, env)

                sh """
                  ${helmTemplateCommand} \\
                  | kubectl --context ${shellQuote(env.KUBE_CONFIG)} apply --dry-run=server -f -
                """
              }
            }
          }
        }
      }
    }

    stage('Deploy Selected Charts') {
      when {
        expression { !params.VALIDATE_ONLY }
      }
      steps {
        withCredentials([
          [
            $class: 'AmazonWebServicesCredentialsBinding',
            accessKeyVariable: 'AWS_ACCESS_KEY_ID',
            credentialsId: env.CRED_ID,
            secretKeyVariable: 'AWS_SECRET_ACCESS_KEY'
          ],
          usernamePassword(
            credentialsId: 'f06cf8c1-1b3c-44e0-bc68-35e0f8a1a6fa',
            usernameVariable: 'USERNAME',
            passwordVariable: 'PASSWORD'
          )
        ]) {
          withEnv([
            "AWS_DEFAULT_REGION=${env.REGION}",
            "AWS_REGION=${env.REGION}",
            "ORIGINAL_KUBECONFIG=${env.KUBECONFIG ?: ''}",
            "KUBECONFIG=${env.WORKSPACE}/.kube-deploy/config",
            "HELM_CONFIG_HOME=${env.WORKSPACE}/.helm-deploy",
            "HELM_CACHE_HOME=${env.WORKSPACE}/.helm-deploy/cache",
            "HELM_DATA_HOME=${env.WORKSPACE}/.helm-deploy/data",
            "HELM_REGISTRY_CONFIG=${env.WORKSPACE}/.helm-deploy/registry/config.json",
            "HELM_EXPERIMENTAL_OCI=1"
          ]) {
            sh '''
              set +x
              mkdir -p "$(dirname "$KUBECONFIG")"
              mkdir -p "$HELM_CONFIG_HOME/registry" "$HELM_CACHE_HOME" "$HELM_DATA_HOME"
              if [ -n "$ORIGINAL_KUBECONFIG" ]; then
                KUBECONFIG="$ORIGINAL_KUBECONFIG" kubectl config view --raw > "$KUBECONFIG"
              else
                env -u KUBECONFIG kubectl config view --raw > "$KUBECONFIG"
              fi
              sed -i 's#client.authentication.k8s.io/v1alpha1#client.authentication.k8s.io/v1beta1#g' "$KUBECONFIG"
              printf '%s' "$PASSWORD" | helm registry login "$ARTIFACTORY_HOST" \
                --username "$USERNAME" \
                --password-stdin
              set -x
            '''

            script {
              def selectedMicroservices = new JsonSlurperClassic().parseText(env.SELECTED_MICROSERVICES_JSON)

              selectedMicroservices.each { microserviceName ->
                def serviceConfig = microserviceCatalog[params.GROUP_NAME].find { it.microserviceName == microserviceName }
                def releaseName = "${microserviceName}-${params.ENV}"
                def helmCommand = this.buildHelmCommand(serviceConfig, releaseName, params, env)

                echo "Applying ${releaseName}"
                sh helmCommand
              }
            }
          }
        }
      }
    }
  }

  post {
    success {
      script {
        if (params.VALIDATE_ONLY) {
          echo 'Validation completed successfully. No releases were applied.'
        } else {
          echo 'Selected microservices were applied successfully.'
        }
      }
    }
    always {
      sh '''
        rm -rf "$WORKSPACE/.helm-validate" "$WORKSPACE/.helm-deploy"
        rm -rf "$WORKSPACE/.kube-validate" "$WORKSPACE/.kube-deploy"
      '''
    }
  }
}
