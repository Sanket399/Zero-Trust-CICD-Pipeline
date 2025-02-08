pipeline {
    agent any
    environment {
        SONAR_SCANNER_HOME = tool 'SonarQube'
        DOCKER_IMAGE = 'zta'  // Only image name
        DOCKER_TAG = "v${BUILD_NUMBER}"
        EC2_HOST = 'ec2-user@34.207.159.185'
        SONAR_HOST_URL = 'http://localhost:9000'
    }
    
    stages {
        stage('Checkout Code') {
            steps {
                git url: 'https://github.com/Sanket399/ZTA_Test_repo.git', branch: 'main'
            }
        }

        stage('SAST SCAN') {
            steps {
                withVault(
                    configuration: [url: 'http://127.0.0.1:8200'],
                    vaultSecrets: [
                        [path: 'secret/sonarqube', secretValues: [
                            [vaultKey: 'token', envVar: 'VAULT_SONAR_TOKEN']
                        ]]
                    ]
                ) {
                    withSonarQubeEnv('SonarQube') {
                        sh """
                            ${SONAR_SCANNER_HOME}/bin/sonar-scanner \
                                -Dsonar.projectKey=my-project \
                                -Dsonar.sources=. \
                                -Dsonar.login=\${VAULT_SONAR_TOKEN}
                        """
                    }
                }
            }
        }

        stage("OWASP Dependency Check") {
          steps {
              dependencyCheck additionalArguments: '--scan ./', odcInstallation: 'OWASP'
              dependencyCheckPublisher pattern: '**/dependency-check-report.xml'
          }
        }

        stage('Build Docker Image') {
            steps {
                script {
                    docker.build("${DOCKER_IMAGE}:${DOCKER_TAG}", "--build-arg BUILD_VERSION=${BUILD_NUMBER} .")
                }
            }
        }
        
        stage('Trivy Docker Image Scan') {
            steps{
                sh "trivy image ${DOCKER_IMAGE}:${DOCKER_TAG} -o trivy-${DOCKER_IMAGE}:${DOCKER_TAG}-report.html"
            }
        }

        stage('Push Images to remote registry') {
            steps {
                script {
                    withVault(
                        configuration: [url: 'http://127.0.0.1:8200'],
                        vaultSecrets: [
                            [path: 'secret/dockerhub', secretValues: [
                                [vaultKey: 'username', envVar: 'DOCKER_USERNAME'],
                                [vaultKey: 'password', envVar: 'DOCKER_PASSWORD']
                            ]]
                        ]
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
                            
                            ssh -o StrictHostKeyChecking=no -i ~/.ssh/temp_key ${EC2_HOST} /bin/bash << 'EOL'

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

        stage('Install Dependencies') {
            steps {
                script {
                    sh 'python3 scripts/install_dependencies.py'
                }
            }
        }

        stage('Find Web Containers') {
            steps {
                script {
                    sh 'python3 scripts/find_viaSSH.py'
                }
            }
        }

        stage('Run Vulnerability Scans') {
            steps {
                script {
                    sh 'python3 scripts/vuln_scan_simplified.py'
                }
            }
        }
    }
    
    post {
        success {
            echo "Pipeline completed successfully"
        }
        failure {
            echo "Pipeline failed. Check logs for details."
        }
    }
}
