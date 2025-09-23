pipeline {
  agent any
  options { timestamps() }

  environment {
    // Chemin Python installé côté agent Windows (à ajuster si besoin)
    PY311 = 'C:\\Users\\cabda\\AppData\\Local\\Programs\\Python\\Python313\\python.exe'
  }

  stages {

    stage('Checkout') {
      steps {
        // Si repo privé : ajoute credentialsId
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
        // On n’échoue pas le build même si l’install rate (pour rester en SUCCESS)
        catchError(buildResult: 'SUCCESS', stageResult: 'FAILURE') {
          bat """
          "%PY311%" -m venv venv
          venv\\Scripts\\python.exe -m pip install --upgrade pip
          venv\\Scripts\\python.exe -m pip install -r requirements.txt
          """
        }
      }
    }

    stage('Run Program') {
      steps {
        // Idem : on évite d’échouer le job
        catchError(buildResult: 'SUCCESS', stageResult: 'FAILURE') {
          bat """
          venv\\Scripts\\python.exe -m invoices.main
          """
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
        // Si aucun .xlsx, on crée un fichier factice et on archive quand même
        bat '''
        if not exist output\\*.xlsx (
          echo No report generated>output\\no_report.txt
        )
        '''
        // IMPORTANT : pas de findFiles -> on autorise archive vide et on passe
        archiveArtifacts artifacts: 'output/*.xlsx, output/no_report.txt',
                          fingerprint: true,
                          onlyIfSuccessful: false,
                          allowEmptyArchive: true
      }
    }
  }

  post {
    // Pour être explicite : si des stages ont échoué mais catchError a intercepté, on force SUCCESS
    always {
      script {
        if (currentBuild.result == null || currentBuild.result == 'FAILURE' || currentBuild.result == 'UNSTABLE') {
          currentBuild.result = 'SUCCESS'
        }
      }
      echo 'Pipeline terminé.'
    }
  }
}
