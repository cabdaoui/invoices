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
                "C:\\Users\\cabda\\AppData\\Local\\Programs\\Python\\Python313\\python.exe" -m venv venv
                call venv\\Scripts\\activate
                "C:\\Users\\cabda\\AppData\\Local\\Programs\\Python\\Python313\\python.exe" -m pip install --upgrade pip
                "C:\\Users\\cabda\\AppData\\Local\\Programs\\Python\\Python313\\python.exe" -m pip install -r requirements.txt
                '''
            }
        }

        stage('Run Program') {
            steps {
                bat '''
                call venv\\Scripts\\activate
                "C:\\Users\\cabda\\AppData\\Local\\Programs\\Python\\Python313\\python.exe" -m invoices.main
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
