import flask
import wtforms
import flask_wtf
import config
import bank_forms
import banco
import pickle
import math

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
	print "La clave secreta del TBanco es: "+bank.getClaveSecreta()

app = flask.Flask(__name__)
app.config.from_object(config.MiConfig)
csrf = flask_wtf.CSRFProtect()

@app.errorhandler(404)
def notFound(error):
	return flask.render_template("notFound.html",page=flask.request.path),404

#Rutas para usuarios

@app.route("/")
def home():
	return flask.render_template("home.html")

@app.route("/register",methods=["GET","POST"])
def register():	
	formulario=bank_forms.RegisterForm(flask.request.form)
	if 'account' in flask.session:
		return flask.redirect(flask.url_for("profile"))
	elif flask.request.method=="POST":
		response={"validation":False}
		if formulario.validate():
			response["validation"]=True
			flask.session["registerID"]=bank.crearCuenta(formulario.password.data)
		else:
			response["errors"]=formulario.errors
		return flask.jsonify(response)
	else:
		return flask.render_template("register.html",form=formulario)

@app.route("/login",methods=["GET","POST"])
def login():
	formulario = bank_forms.LoginForm(bank)(flask.request.form)
	if 'account' in flask.session:
		return flask.redirect(flask.url_for("profile"))
	elif flask.request.method=="POST":
		response = {"validation":False}
		if formulario.validate():
			flask.session["account"]=formulario.account.data
			flask.session["password"]=formulario.password.data
			response["validation"]=True
		else:
			response["errors"]=formulario.errors
		return flask.jsonify(response)
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

@app.route("/mi_cuenta/")
@app.route("/mi_cuenta/<int:page>")
def profile(page=1):
	if 'account' in flask.session:
		cuenta=bank.obtenerCuenta(flask.session['account'],flask.session['password'])
		cuenta['cuenta'].actualizarSaldo()
		monedas=banco.paginarMonedas(cuenta["cuenta"],page)
		if monedas['error']:
			return flask.render_template("cuenta.html",cuenta=True,monedas=monedas)
		else:
			return flask.render_template("cuenta.html",
				cuenta=cuenta['cuenta'],
				nmonedas=cuenta['monedas'],
				monedas=[moneda.__json__() for moneda in monedas['monedas']],
				npages=(lambda a,b:(a/b)+1 if a%b else (a/b))(cuenta['monedas'],20),
				page=page,
				last_page=monedas['last_page']
			)
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
		cuenta = bank.obtenerCuenta(flask.session['account'],flask.session['password'])["cuenta"]
		if cuenta.permisos():
			return flask.render_template("admin_main.html",admin=cuenta.getID())
		else:
			return flask.redirect(flask.url_for('profile'))
	else:
		return flask.redirect(flask.url_for('home'))

@app.route("/admin/cuenta/<cuenta_id>/")
@app.route("/admin/cuenta/<cuenta_id>/<int:page>")
def informacion_cuenta(cuenta_id,page=1):
	if 'account' in flask.session:
		cuenta = bank.obtenerCuenta(flask.session['account'],flask.session['password'])["cuenta"]
		if cuenta.permisos():
			cuenta = bank.obtenerCuenta(cuenta_id,admin=cuenta)
			if cuenta: 
				cuenta['cuenta'].actualizarSaldo()
				monedas=banco.paginarMonedas(cuenta["cuenta"],page)
				if monedas['error']:
					return flask.render_template("cuenta.html",cuenta=True,monedas=monedas)
				else:
					return flask.render_template("cuenta.html",
						cuenta=cuenta['cuenta'],
						nmonedas=cuenta['monedas'],
						monedas=[moneda.__json__() for moneda in monedas['monedas']],
						npages=(lambda a,b:(a/b)+1 if a%b else (a/b))(cuenta['monedas'],20),
						page=page,
						last_page=monedas['last_page']
					)
			else:
				return flask.render_template("cuenta.html",cuentaID=cuenta_id)
		else:
			return flask.redirect(flask.url_for('profile'))
	else:
		return flask.redirect(flask.url_for('login'))

@app.route("/admin/cuentas/")
@app.route("/admin/cuentas/<int:page>")
def informacion_cuentas(page=1):
	if 'account' in flask.session:
		cuenta = bank.obtenerCuenta(flask.session['account'],flask.session['password'])["cuenta"]
		if cuenta.permisos():
			return flask.render_template("cuentas.html",cuentas=bank.obtenerCuentas(cuenta,page=page))
		else:
			return flask.redirect(flask.url_for("profile"))
	else:
		return flask.redirect(flask.url_for('login'))

if __name__=="__main__":
	csrf.init_app(app)
	app.run(port=8080)
#Luis Albizo 2017-01-20