import re
import wtforms

def IDValida(form,field):
	if not(bool(re.match(r"\w+",field.data))):
		raise wtforms.validators.ValidationError("ID con formato invalido, caracteres aceptados: \"a-zA-Z0-9_\" (el '-' no es aceptado')")

def CuentaExiste(instanciaBanco):
	def CCuentaExiste(form,field):
		if instanciaBanco.obtenerCuenta(field.data,"_")==None:
			raise wtforms.validators.ValidationError("La cuenta \""+field.data+"\" no existe")
	return CCuentaExiste

def Autenticacion(instanciaBanco):
	def auth(form,field):
		if instanciaBanco.obtenerCuenta(form.account.data,field.data)==False:
			raise wtforms.validators.ValidationError("Error de autenticacion: clave incorrecta")
	return auth

def Coinciden(confirmacion):
	def CCoinciden(form,field):
		if confirmacion.data!=field.data:
			raise wtforms.validators.ValidationError("La confirmacion no coincide")
	return CCoinciden

#
def LoginForm(instanciaBanco):
	class CAccountForm(wtforms.Form):
		account = wtforms.StringField(
			"ID de cuenta",
			[
				wtforms.validators.Required(message="El ID es requerido"),
				wtforms.validators.length(min=8,max=8,message="El ID debe contener exactamente 8 caracteres"),
				IDValida,
				CuentaExiste(instanciaBanco)
			]
		)
		password = wtforms.PasswordField(
			"Clave",
			[
				wtforms.validators.Required(message="La clave es requerida"),
				Autenticacion(instanciaBanco)
			]
		)
	return CAccountForm

class RegisterForm(wtforms.Form):
	password = wtforms.PasswordField(
		"Clave",
		[
			wtforms.validators.Required(message="El campo contrasena no debe estar vacio"),
			wtforms.validators.length(min=6,max=32,message="La contrasena debe tener al menos 6 caracteres y maximo 32")
		]
	)

	confirm = wtforms.PasswordField(
		"Confirma tu clave",
		[
			wtforms.validators.Required(message="El campo de confirmacion no debe estar vacio")
		]
	)

	def validate_confirm(form,field):
		if field.data != form.password.data:
			raise wtforms.validators.ValidationError("Las claves no coinciden")


