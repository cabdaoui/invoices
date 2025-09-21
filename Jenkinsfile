pipeline {
    agent any

    stages {
        stage('Checkout') {
            steps {
                git branch: 'main',
                    url: 'https://github.com/cabdaoui/invoices.git'
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
