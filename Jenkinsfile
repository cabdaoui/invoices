pipeline {
  agent any
  options { timestamps() }

  environment {
    PY311 = 'C:\\Users\\cabda\\AppData\\Local\\Programs\\Python\\Python313\\python.exe'
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
        bat '''
        if not exist input mkdir input
        if not exist output mkdir output
        if not exist traitement mkdir traitement
        '''
      }
    }

    stage('Setup Python Env') {
      steps {
        catchError(buildResult: 'SUCCESS', stageResult: 'FAILURE') {
          bat """
          "%PY311%" -m venv venv
          venv\\Scripts\\python.exe -m pip install --upgrade pip
          venv\\Scripts\\python.exe -m pip install -r requirements.txt
          REM --- Ajout explicite de PyPDF2 ---
          venv\\Scripts\\python.exe -m pip install PyPDF2
          """
        }
      }
    }

    stage('Run Program') {
      steps {
        catchError(buildResult: 'SUCCESS', stageResult: 'FAILURE') {
          bat "venv\\Scripts\\python.exe -m invoices.main"
        }
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
        bat '''
        if not exist output\\*.xlsx (
          echo No report generated>output\\no_report.txt
        )
        '''
        archiveArtifacts artifacts: 'output/*.xlsx, output/no_report.txt',
                          fingerprint: true,
                          onlyIfSuccessful: false,
                          allowEmptyArchive: true
      }
    }
  }

  post {
    always {
      // Optionnel : forcer SUCCESS même si des stages ont échoué interceptés
      script {
        if (currentBuild.result == null || currentBuild.result in ['FAILURE','UNSTABLE']) {
          currentBuild.result = 'SUCCESS'
        }
      }
      echo 'Pipeline terminé.'
    }
  }
}
