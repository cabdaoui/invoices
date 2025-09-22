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

        stage('Debug Files') {
            steps {
                bat 'dir'
                bat 'dir output'
            }
        }

        stage('Archive Report') {
            steps {
                script {
                    // Vérifie si un fichier Excel existe
                    def files = findFiles(glob: 'output/*.xlsx')
                    if (files.length > 0) {
                        archiveArtifacts artifacts: 'output/*.xlsx', fingerprint: true
                    } else {
                        echo "⚠️ Aucun fichier Excel trouvé dans output/. Création d’un fichier factice..."
                        bat 'echo "No report generated" > output\\no_report.txt'
                        archiveArtifacts artifacts: 'output/no_report.txt', fingerprint: true
                    }
                }
            }
        }
    }
}
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

        stage('Debug Files') {
            steps {
                bat 'dir'
                bat 'dir output'
            }
        }

        stage('Archive Report') {
            steps {
                script {
                    // Vérifie si un fichier Excel existe
                    def files = findFiles(glob: 'output/*.xlsx')
                    if (files.length > 0) {
                        archiveArtifacts artifacts: 'output/*.xlsx', fingerprint: true
                    } else {
                        echo "⚠️ Aucun fichier Excel trouvé dans output/. Création d’un fichier factice..."
                        bat 'echo "No report generated" > output\\no_report.txt'
                        archiveArtifacts artifacts: 'output/no_report.txt', fingerprint: true
                    }
                }
            }
        }
    }
}
