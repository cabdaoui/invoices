pipeline {
    agent any

    tools {
        python 'Python3'
    }

    stages {
        stage('Checkout') {
            steps {
                git branch: 'main',
                    url: 'https://github.com/cabdaoui/Robots.git'
            }
        }

        stage('Setup Python Env') {
            steps {
                bat '''
                python -m venv venv
                call venv\\Scripts\\activate
                pip install --upgrade pip
                pip install -r requirements.txt
                '''
            }
        }

        stage('Run Program') {
            steps {
                bat '''
                call venv\\Scripts\\activate
                python -m invoices.main
                '''
            }
        }

        stage('Archive Report') {
            steps {
                archiveArtifacts artifacts: 'output/*.xlsx', fingerprint: true
            }
        }
    }
}
