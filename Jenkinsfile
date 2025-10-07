pipeline {
  agent any
  options { timestamps() }

  environment {
    // Chemin Python : ajuste si nécessaire
    PYTHON_EXE = 'C:\\Users\\cabda\\AppData\\Local\\Programs\\Python\\Python313\\python.exe'
  }

  stages {
    stage('Checkout') {
      steps {
        git branch: 'main',
            url: 'https://github.com/cabdaoui/invoices.git',
            credentialsId: 'github-token'
      }
    }

    stage('Prepare Folders') {
      steps {
        bat 'if not exist input mkdir input'
        bat 'if not exist output mkdir output'
        bat 'if not exist traitement mkdir traitement'
      }
    }

    stage('Setup Python Env') {
      steps {
        // Pas de GString multiline pour éviter certains parseurs groovy capricieux
        bat "\"%PYTHON_EXE%\" -m venv venv"
        bat "venv\\Scripts\\python.exe -m pip install --upgrade pip"
        // Installe requirements si présent (sinon, on continue)
        bat "if exist requirements.txt venv\\Scripts\\python.exe -m pip install -r requirements.txt"
        // Installation explicite de PyPDF2 (au cas où non listé dans requirements)
        bat "venv\\Scripts\\python.exe -m pip install PyPDF2"
      }
    }

    stage('Run Program') {
      steps {
        bat "venv\\Scripts\\python.exe -m invoices.main"
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
        // Crée un marqueur si aucun .xlsx
        bat "if not exist output\\*.xlsx echo No report generated>output\\no_report.txt"
        archiveArtifacts artifacts: 'output/*.xlsx, output/no_report.txt',
                         fingerprint: true,
                         onlyIfSuccessful: false,
                         allowEmptyArchive: true
      }
    }
  }

  post {
    always {
      echo 'Pipeline terminé.'
    }
  }
}
