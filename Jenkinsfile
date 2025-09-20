pipeline {
    agent any

    environment {
        // Optionnel : forcer l’UTF-8 (utile si accents)
        PYTHONIOENCODING = 'utf-8'
    }

    stages {
        stage('Checkout') {
            steps {
                echo "📥 Clonage du projet..."
                checkout scm
            }
        }

        stage('Setup Python') {
            steps {
                echo "🐍 Installation des dépendances Python..."
                // Installe les requirements dans un venv isolé
                sh '''
                python -m venv venv
                . venv/bin/activate
                pip install --upgrade pip
                pip install -r requirements.txt
                '''
            }
        }

        stage('Run Pipeline') {
            steps {
                echo "🚀 Exécution du pipeline factures..."
                sh '''
                . venv/bin/activate
                python -m invoices.main
                '''
            }
        }

        stage('Archive Reporting') {
            steps {
                echo "📦 Archivage du reporting Excel..."
                archiveArtifacts artifacts: 'traitement/Reporting_invoices.xlsx', fingerprint: true
            }
        }
    }

    post {
        always {
            echo "✅ Pipeline terminé (succès ou échec)"
        }
        success {
            echo "🎉 Succès du pipeline"
        }
        failure {
            echo "💥 Le pipeline a échoué"
        }
    }
}
