from werkzeug.middleware.proxy_fix import ProxyFix
from app import app

app.config['PREFERRED_URL_SCHEME'] = 'https'

app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1)

# Change port if rquired: default is 5000 for flask
if __name__ == '__main__':
    app.run(debug=False, port=6002)

# create a WSGI application object
application = app
