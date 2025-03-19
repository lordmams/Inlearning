import http.server
import socketserver
import os
import webbrowser

# Création du répertoire templates s'il n'existe pas
os.makedirs('templates', exist_ok=True)

# Créer la page d'index
with open('index.html', 'w', encoding='utf-8') as f:
    f.write('''
<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Aperçu des formulaires</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0-alpha1/dist/css/bootstrap.min.css" rel="stylesheet">
    <style>
        .preview-container {
            max-width: 600px;
            margin: 100px auto;
            padding: 30px;
            border-radius: 10px;
            box-shadow: 0 0 15px rgba(0, 0, 0, 0.1);
            background-color: #fff;
        }
        .preview-title {
            text-align: center;
            margin-bottom: 30px;
            color: #0d6efd;
        }
        .preview-link {
            display: block;
            padding: 15px;
            margin-bottom: 15px;
            background-color: #f8f9fa;
            border-radius: 5px;
            text-decoration: none;
            color: #0d6efd;
            font-weight: bold;
            text-align: center;
            transition: all 0.3s ease;
        }
        .preview-link:hover {
            background-color: #e9ecef;
            transform: translateY(-2px);
        }
        body {
            background-color: #f0f2f5;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="preview-container">
            <h2 class="preview-title">Aperçu des formulaires</h2>
            <a href="templates/login.html" class="preview-link">Formulaire de connexion</a>
            <a href="templates/register.html" class="preview-link">Formulaire d'inscription</a>
            <a href="templates/profile_form.html" class="preview-link">Formulaire de profil utilisateur</a>
        </div>
    </div>
    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0-alpha1/dist/js/bootstrap.bundle.min.js"></script>
</body>
</html>
    ''')

# Copiez ici les templates HTML fournis précédemment
# (login.html, register.html, profile_form.html)
with open('templates/login.html', 'w', encoding='utf-8') as f:
    f.write('''
<!-- Insérez ici le contenu HTML du formulaire de connexion -->
<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Connexion</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0-alpha1/dist/css/bootstrap.min.css" rel="stylesheet">
    <style>
        .login-container {
            max-width: 450px;
            margin: 100px auto;
            padding: 20px;
            border-radius: 10px;
            box-shadow: 0 0 15px rgba(0, 0, 0, 0.1);
            background-color: #fff;
        }
        .login-title {
            text-align: center;
            margin-bottom: 30px;
            color: #0d6efd;
        }
        .btn-login {
            width: 100%;
            padding: 10px;
            margin-top: 15px;
        }
        .register-link {
            text-align: center;
            margin-top: 20px;
        }
        body {
            background-color: #f8f9fa;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="login-container">
            <h2 class="login-title">Connexion</h2>
            
            <form method="post" action="">
                <div class="mb-3">
                    <label for="username" class="form-label">Nom d'utilisateur ou Email</label>
                    <input type="text" class="form-control" id="username" name="username" required>
                </div>
                
                <div class="mb-3">
                    <label for="password" class="form-label">Mot de passe</label>
                    <input type="password" class="form-control" id="password" name="password" required>
                </div>
                
                <div class="mb-3 form-check">
                    <input type="checkbox" class="form-check-input" id="remember" name="remember">
                    <label class="form-check-label" for="remember">Se souvenir de moi</label>
                </div>
                
                <button type="submit" class="btn btn-primary btn-login">Se connecter</button>
            </form>
            
            <div class="register-link">
                <p>Vous n'avez pas de compte ? <a href="register.html">S'inscrire</a></p>
                <p><a href="#">Mot de passe oublié ?</a></p>
            </div>
        </div>
    </div>
    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0-alpha1/dist/js/bootstrap.bundle.min.js"></script>
</body>
</html>
    ''')

# Démmarrage du serveur
PORT = 8000
Handler = http.server.SimpleHTTPRequestHandler

with socketserver.TCPServer(("", PORT), Handler) as httpd:
    print(f"Serveur lancé sur http://localhost:{PORT}")
    # Ouvrir automatiquement le navigateur
    webbrowser.open(f'http://localhost:{PORT}')
    httpd.serve_forever()