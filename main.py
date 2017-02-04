import flask
import wtforms
import flask_wtf
import config
import bank_forms
import banco
import pickle

try:
	f=open("data/bank.pk","rb")
	bank = pickle.load(f)
	f.close()
	print "Actual TBanco cargado"
except:
	bank = banco.TBanco("flask_bank")
	f=open("data/bank.pk","wb")
	pickle.dump(bank,f)
	f.close()
	f=open("data/bank_key.txt","wb")
	f.write(bank.getClaveSecreta())
	f.close()
	print "Nuevo TBanco creado"
finally:
	del f
	print "La clave secreta delTBanco es: "+bank.getClaveSecreta()

app = flask.Flask(__name__)
app.config.from_object(config.MiConfig)
csrf = flask_wtf.CSRFProtect()

for _ in range(50):
	bank.crearCuenta("pass")

@app.errorhandler(404)
def notFound(error):
	return flask.render_template("notFound.html",page=flask.request.path),404

#Rutas para usuarios

@app.route("/")
def home():
	return flask.render_template("home.html")

@app.route("/register",methods=["GET","POST"])
def register():	
	register=bank_forms.RegisterForm(flask.request.form)
	if 'account' in flask.session:
		return flask.redirect(flask.url_for("profile"))
	elif flask.request.method=="POST" and register.validate():
		cuenta = bank.crearCuenta(register.password.data)
		flask.session["registerID"]=cuenta
		return flask.redirect(flask.url_for('login'))
	else:
		return flask.render_template("register.html",form=register)

@app.route("/login",methods=["GET","POST"])
def login():
	formulario = bank_forms.LoginForm(bank)(flask.request.form)
	if 'account' in flask.session:
		return flask.redirect(flask.url_for("profile"))
	elif flask.request.method=="POST" and formulario.validate():
		flask.session["account"]=formulario.account.data
		flask.session["password"]=formulario.password.data
		return flask.redirect(flask.url_for("profile"))
	else:
		account_value=""
		alert=None
		if 'registerID' in flask.session:
			alert = "Te has registrado correctamente, tu ID es: "+flask.session['registerID']
			account_value = flask.session['registerID']
			flask.session.pop('registerID')
		elif flask.request.method=="POST":
			account_value = flask.request.form["account"]
		return flask.render_template("login.html",form=formulario,alert=alert,account_value=account_value)

@app.route("/mi_cuenta")
def profile():
	if 'account' in flask.session:
		cuenta=bank.obtenerCuenta(flask.session['account'],flask.session['password'])
		return flask.render_template("cuenta.html",cuenta=cuenta)
	else:
		return flask.redirect(flask.url_for("login"))

@app.route("/logout")
def logout():
	try:
		flask.session.pop("account")
		flask.session.pop("password")
	except:
		pass
	return flask.redirect(flask.url_for("login"))

#Rutas para administrador

@app.route("/admin/")
def admin_main():
	if 'account' in flask.session:
		cuenta = bank.obtenerCuenta(flask.session['account'],flask.session['password'])
		if cuenta.permisos():
			return flask.render_template("admin_main.html",permisos=True,cuenta=cuenta)
		else:
			return flask.redirect(flask.url_for('profile'))
	else:
		return flask.redirect(flask.url_for('home'))

@app.route("/admin/cuentas/<cuenta_id>")
def informacion_cuenta(cuenta_id):
	if 'account' in flask.session:
		cuenta = bank.obtenerCuenta(flask.session['account'],flask.session['password'])
		if cuenta.permisos():
			cuenta = bank.obtenerCuenta(cuenta_id,admin=cuenta)
			if cuenta: 
				return flask.render_template("cuenta.html",cuenta=cuenta)
			else:
				return flask.render_template("cuenta.html",cuentaID=cuenta_id)
		else:
			return flask.redirect(flask.url_for('profile'))
	else:
		return flask.redirect(flask.url_for('login'))

@app.route("/admin/cuentas/")
def informacion_cuentas():
	if 'account' in flask.session:
		cuenta = bank.obtenerCuenta(flask.session['account'],flask.session['password'])
		if cuenta.permisos():
			return flask.render_template("cuentas.html",cuentas=bank.obtenerCuentas(cuenta))
		else:
			return flask.redirect(flask.url_for("profile"))
	else:
		return flask.redirect(flask.url_for('login'))

if __name__=="__main__":
	csrf.init_app(app)
	app.run(port=8080)

