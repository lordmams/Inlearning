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
            <a href="login.html" class="preview-link">Formulaire de connexion</a>
            <a href="register.html" class="preview-link">Formulaire d'inscription</a>
            <a href="profile_form.html" class="preview-link">Formulaire de profil utilisateur</a>
        </div>
    </div>
    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0-alpha1/dist/js/bootstrap.bundle.min.js"></script>
</body>
</html>
    ''')

# Formulaire de connexion
with open('login.html', 'w', encoding='utf-8') as f:
    f.write('''
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

# Formulaire d'inscription
with open('register.html', 'w', encoding='utf-8') as f:
    f.write('''
<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Inscription</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0-alpha1/dist/css/bootstrap.min.css" rel="stylesheet">
    <style>
        .register-container {
            max-width: 550px;
            margin: 50px auto;
            padding: 25px;
            border-radius: 10px;
            box-shadow: 0 0 15px rgba(0, 0, 0, 0.1);
            background-color: #fff;
        }
        .register-title {
            text-align: center;
            margin-bottom: 30px;
            color: #0d6efd;
        }
        .btn-register {
            width: 100%;
            padding: 10px;
            margin-top: 15px;
        }
        .login-link {
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
        <div class="register-container">
            <h2 class="register-title">Créer un compte</h2>
            
            <form method="post" action="">
                <div class="row mb-3">
                    <div class="col-md-6">
                        <label for="firstname" class="form-label">Prénom</label>
                        <input type="text" class="form-control" id="firstname" name="firstname" required>
                    </div>
                    <div class="col-md-6">
                        <label for="lastname" class="form-label">Nom</label>
                        <input type="text" class="form-control" id="lastname" name="lastname" required>
                    </div>
                </div>
                
                <div class="mb-3">
                    <label for="email" class="form-label">Adresse email</label>
                    <input type="email" class="form-control" id="email" name="email" required>
                </div>
                
                <div class="mb-3">
                    <label for="phone" class="form-label">Numéro de téléphone</label>
                    <input type="tel" class="form-control" id="phone" name="phone">
                </div>
                
                <div class="mb-3">
                    <label for="username" class="form-label">Nom d'utilisateur</label>
                    <input type="text" class="form-control" id="username" name="username" required>
                </div>
                
                <div class="row mb-3">
                    <div class="col-md-6">
                        <label for="password" class="form-label">Mot de passe</label>
                        <input type="password" class="form-control" id="password" name="password" required>
                    </div>
                    <div class="col-md-6">
                        <label for="confirm_password" class="form-label">Confirmer le mot de passe</label>
                        <input type="password" class="form-control" id="confirm_password" name="confirm_password" required>
                    </div>
                </div>
                
                <div class="mb-3 form-check">
                    <input type="checkbox" class="form-check-input" id="terms" name="terms" required>
                    <label class="form-check-label" for="terms">J'accepte les <a href="#">termes et conditions</a></label>
                </div>
                
                <button type="submit" class="btn btn-primary btn-register">S'inscrire</button>
            </form>
            
            <div class="login-link">
                <p>Vous avez déjà un compte ? <a href="login.html">Se connecter</a></p>
            </div>
        </div>
    </div>
    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0-alpha1/dist/js/bootstrap.bundle.min.js"></script>
</body>
</html>
    ''')

# Formulaire de profil
with open('profile_form.html', 'w', encoding='utf-8') as f:
    f.write('''
<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Formulaire de Profil Utilisateur</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0-alpha1/dist/css/bootstrap.min.css" rel="stylesheet">
    <style>
        .form-section {
            background-color: #f8f9fa;
            padding: 20px;
            border-radius: 5px;
            margin-bottom: 20px;
        }
        .section-title {
            border-bottom: 2px solid #0d6efd;
            padding-bottom: 5px;
            margin-bottom: 15px;
        }
        .delete-row {
            color: #dc3545;
            cursor: pointer;
        }
        .add-row {
            margin-top: 10px;
        }
    </style>
</head>
<body>
    <div class="container py-5">
        <h1 class="mb-4 text-center">Formulaire de Profil Utilisateur</h1>
        
        <form method="post" class="needs-validation" novalidate>
            <!-- Informations personnelles -->
            <div class="form-section">
                <h3 class="section-title">Informations Personnelles</h3>
                <div class="row g-3">
                    <div class="col-md-6">
                        <label class="form-label">Nom complet</label>
                        <input type="text" class="form-control" placeholder="Votre nom complet">
                    </div>
                    <div class="col-md-2">
                        <label class="form-label">Âge</label>
                        <input type="number" class="form-control" placeholder="Âge">
                    </div>
                    <div class="col-md-4">
                        <label class="form-label">Sexe</label>
                        <select class="form-select">
                            <option value="">Choisir...</option>
                            <option>Masculin</option>
                            <option>Féminin</option>
                            <option>Autre</option>
                            <option>Préfère ne pas préciser</option>
                        </select>
                    </div>
                    <div class="col-md-6">
                        <label class="form-label">Adresse e-mail</label>
                        <input type="email" class="form-control" placeholder="email@exemple.com">
                    </div>
                    <div class="col-md-6">
                        <label class="form-label">Numéro de téléphone</label>
                        <input type="tel" class="form-control" placeholder="Votre numéro">
                    </div>
                </div>
            </div>
            
            <!-- Préférences -->
            <div class="form-section">
                <h3 class="section-title">Préférences</h3>
                <div class="row g-3 mb-3">
                    <div class="col-md-6">
                        <label class="form-label">Langue préférée</label>
                        <select class="form-select">
                            <option value="">Choisir...</option>
                            <option>Français</option>
                            <option>Anglais</option>
                            <option>Espagnol</option>
                            <option>Allemand</option>
                            <option>Chinois</option>
                            <option>Arabe</option>
                        </select>
                    </div>
                    <div class="col-md-6">
                        <label class="form-label">Mode d'apprentissage préféré</label>
                        <select class="form-select">
                            <option value="">Choisir...</option>
                            <option>En ligne</option>
                            <option>Présentiel</option>
                            <option>Mixte</option>
                        </select>
                    </div>
                </div>
                
                <h4>Centres d'intérêt</h4>
                <table class="table table-bordered table-hover">
                    <thead class="table-light">
                        <tr>
                            <th>Centre d'intérêt</th>
                            <th width="10%">Supprimer</th>
                        </tr>
                    </thead>
                    <tbody>
                        <tr>
                            <td>
                                <input type="text" class="form-control" placeholder="Votre centre d'intérêt">
                            </td>
                            <td class="text-center">
                                <input type="checkbox" class="form-check-input">
                            </td>
                        </tr>
                        <tr>
                            <td>
                                <input type="text" class="form-control" placeholder="Votre centre d'intérêt">
                            </td>
                            <td class="text-center">
                                <input type="checkbox" class="form-check-input">
                            </td>
                        </tr>
                    </tbody>
                </table>
                <button type="button" class="btn btn-sm btn-outline-primary add-row">Ajouter un centre d'intérêt</button>
            </div>
            
            <!-- Parcours académique et professionnel simplifié pour l'aperçu -->
            <div class="form-section">
                <h3 class="section-title">Parcours Académique</h3>
                <div class="row g-3 mb-3">
                    <div class="col-md-6">
                        <label class="form-label">Niveau académique atteint</label>
                        <select class="form-select">
                            <option value="">Choisir...</option>
                            <option>Baccalauréat</option>
                            <option>Licence</option>
                            <option>Master</option>
                            <option>Doctorat</option>
                            <option>Autre</option>
                        </select>
                    </div>
                </div>
            </div>
            
            <!-- Boutons d'action -->
            <div class="d-grid gap-2 d-md-flex justify-content-md-end mt-4">
                <button type="submit" class="btn btn-primary">Enregistrer le profil</button>
            </div>
        </form>
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