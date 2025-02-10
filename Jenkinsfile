pipeline {
    agent any
    environment {
        SONAR_SCANNER_HOME = tool 'SonarQube'
        DOCKER_IMAGE = 'zta'
        DOCKER_TAG = "v${BUILD_NUMBER}"
        SONAR_HOST_URL = 'http://localhost:9000'
        APP_CODE_DIR = 'app'
    }
    
    stages {
        stage('Code Checkout & Setup') {
            stages {
                stage('Checkout Infrastructure Code') {
                    steps {
                        checkout scm
                    }
                }
               
                stage('Checkout Application Code') {
                    steps {
                        withVault(
                            configuration: [
                                vaultUrl: 'http://127.0.0.1:8200',  // Correct parameter name
                                engineVersion: 2
                            ],
                            vaultSecrets: [[
                                path: 'secret/github',
                                secretValues: [[vaultKey: 'token', envVar: 'GITHUB_TOKEN']]
                            ]]
                        ) {
                            script {

                                sh """
                                    if [ -d "${APP_CODE_DIR}" ]; then
                                        rm -rf ${APP_CODE_DIR}
                                    fi
                                """

                                sh """
                                    git clone https://${GITHUB_TOKEN}@github.com/Sanket399/ZTA-ApplicationCode.git ${APP_CODE_DIR}
                                """
                            }
                        }
                    }
                }

                stage('Install Dependencies') {
                    steps {
                        script {
                            sh 'python3 scripts/install_dependencies.py'
                        }
                    }
                }
            }
        }

        stage('Static Analysis') {
            stages {
                stage('SonarQube Analysis') {
                    steps {
                        withVault(
                            configuration: [url: 'http://127.0.0.1:8200'],
                            vaultSecrets: [[
                                path: 'secret/sonarqube',
                                secretValues: [[vaultKey: 'token', envVar: 'VAULT_SONAR_TOKEN']]
                            ]]
                        ) {
                            withSonarQubeEnv('SonarQube') {
                                sh """
                                    ${SONAR_SCANNER_HOME}/bin/sonar-scanner \
                                        -Dsonar.projectKey=ZTA-test-application \
                                        -Dsonar.sources=. \
                                        -Dsonar.login=\${VAULT_SONAR_TOKEN}
                                """
                            }
                        }
                    }
                }
                
                stage("Dependency Check") {
                    steps {
                        dependencyCheck additionalArguments: '--scan ./', odcInstallation: 'OWASP'
                        dependencyCheckPublisher pattern: '**/dependency-check-report.xml'
                    }
                }
            }
        }

        stage('Container Build & Security') {
            stages {
                stage('Build Docker Image') {
                    steps {
                        script {
                            docker.build("${DOCKER_IMAGE}:${DOCKER_TAG}", "--build-arg BUILD_VERSION=${BUILD_NUMBER} ${APP_CODE_DIR}")
                        }
                    }
                }
                
                stage('Container Security Scan') {
                    steps {
                        script {
                            // Create a timestamped directory for this build's security reports
                            def reportDir = "security-reports/${BUILD_NUMBER}"
                            sh "mkdir -p ${reportDir}"
                            
                            // Run Trivy scan with multiple report formats                           

                            sh """

                                trivy image ${DOCKER_IMAGE}:${DOCKER_TAG} \
                                    --format template \
                                    --template '@/usr/local/share/trivy/templates/html.tpl' \
                                    --output ${reportDir}/trivy-report.html \
                                    --exit-code 0 
                                    --secerity HIGH, CRITICAL

                                trivy image ${DOCKER_IMAGE}:${DOCKER_TAG} \
                                    --format json \
                                    -o ${reportDir}/trivy-report.json \
                                    --exit-code 1 \
                                    --severity HIGH,CRITICAL
                            

                                trivy fs ${APP_CODE_DIR} \
                                    -o ${reportDir}/trivy-fs-report.html \
                                    --format template \
                                    --template '/usr/local/share/trivy/templates/html.tpl' \
                                    --security-checks vuln,config,secret \
                                    --exit-code 0

                                trivy fs ${APP_CODE_DIR} \
                                    -o ${reportDir}/trivy-fs-report.json \
                                    --format json \
                                    --security-checks vuln,config,secret \
                                    --exit-code 1 \
                                    --severity HIGH,CRITICAL
                            """
                            // Archive the reports
                            archiveArtifacts artifacts: "${reportDir}/**/*", allowEmptyArchive: true
                            
                            // Optional: Clean up old reports (keep last 10 builds)
                            sh """
                                cd security-reports && ls -t | tail -n +11 | xargs rm -rf
                            """
                        }
                    }
                }
            }
        }

        stage('Deployment') {
            stages {
                stage('Push to Registry') {
                    steps {
                        script {
                            withVault(
                                configuration: [url: 'http://127.0.0.1:8200'],
                                vaultSecrets: [[
                                    path: 'secret/dockerhub',
                                    secretValues: [
                                        [vaultKey: 'username', envVar: 'DOCKER_USERNAME'],
                                        [vaultKey: 'password', envVar: 'DOCKER_PASSWORD']
                                    ]
                                ]]
                            ) {
                                sh """
                                    echo \$DOCKER_PASSWORD | docker login -u \$DOCKER_USERNAME --password-stdin
                                    docker tag "${DOCKER_IMAGE}:${DOCKER_TAG}" "\${DOCKER_USERNAME}/${DOCKER_IMAGE}:${DOCKER_TAG}"
                                    docker tag "${DOCKER_IMAGE}:${DOCKER_TAG}" "\${DOCKER_USERNAME}/${DOCKER_IMAGE}:latest"
                                    docker push "\${DOCKER_USERNAME}/${DOCKER_IMAGE}:${DOCKER_TAG}"
                                    docker push "\${DOCKER_USERNAME}/${DOCKER_IMAGE}:latest"
                                """
                            }
                        }
                    }
                }
                
                stage('Deploy to EC2') {
                    steps {
                        script {
                            withVault(
                        configuration: [url: 'http://127.0.0.1:8200'],
                        vaultSecrets: [
                            [path: 'secret/ssh', secretValues: [
                                [vaultKey: 'private_key', envVar: 'SSH_PRIVATE_KEY']
                            ]],
                            [path: 'secret/dockerhub', secretValues: [
                                [vaultKey: 'username', envVar: 'DOCKER_USERNAME']
                            ]],
                            [path: 'secret/ec2-host', secretValues: [
                                [vaultKey: 'ec2-host', envVar: 'EC2_HOST']
                            ]]
                        ]
                            ) {
                                
                                def dockerUsername = sh(script: 'echo $DOCKER_USERNAME', returnStdout: true).trim()
                                def dockerImage = env.DOCKER_IMAGE
                                def dockerTag = env.DOCKER_TAG
                                
                                sh """
                                    mkdir -p ~/.ssh
                                    echo "\$SSH_PRIVATE_KEY" > ~/.ssh/temp_key
                                    chmod 600 ~/.ssh/temp_key
                                    
                                    ssh -o StrictHostKeyChecking=no -i ~/.ssh/temp_key \${EC2_HOST} /bin/bash << 'EOL'
        
                                    docker pull ${dockerUsername}/${dockerImage}:${dockerTag}
                                    docker stop zta-container || true
                                    docker rm zta-container || true
                                    docker run -d \
                                        --name zta-container \
                                        -p 80:80 \
                                        -p 443:443 \
                                        -v /home/ec2-user/nginx-container/html:/usr/share/nginx/html \
                                        -v /home/ec2-user/nginx-container/conf/nginx.conf:/etc/nginx/conf.d/default.conf \
                                        -v /etc/letsencrypt:/etc/letsencrypt \
                                        ${dockerUsername}/${dockerImage}:${dockerTag}
                                    
                                    docker ps | grep zta-container
                                    EOL
                                    
                                    rm -f ~/.ssh/temp_key
                                """
                            }
                        }
                    }
                }
            }
        }

        stage('Security Testing') {
            stages {
                stage('Discover Web Services') {
                    steps {
                        script {
                            sh 'python3 scripts/find_viaSSH.py'
                        }
                    }
                }

                stage('Security Scans') {
                    steps {
                        script {
                            sh 'python3 scripts/vuln_scan_simplified.py'
                        }
                    }
                }
            }
        }
        
        stage('Deploy Monitoring Containers') {
            steps {
                sh '''
                # Activate Python environment if needed
                python3 scripts/deploy_monitoring_containers.py
                '''
            }
        }
    }
    
    post {
        always {
            archiveArtifacts artifacts: '**/trivy-*.html, **/dependency-check-report.xml', allowEmptyArchive: true
        }
        success {
            echo "Pipeline completed successfully"
        }
        failure {
            echo "Pipeline failed. Check logs for details."
        }
    }
}
