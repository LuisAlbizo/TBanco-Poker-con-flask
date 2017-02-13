import time, pickle, base64, threading, os
from peewee import SqliteDatabase, Model, TextField, CharField, IntegerField, BooleanField, ForeignKeyField
from functools import reduce
import tools.tools as tools

#Los modelos o Schemas de mi DB
class ObjectField(TextField):
	def python_value(self,value):
		return pickle.loads(base64.b64decode(value).encode())

	def db_value(self,value):
		return base64.b64encode(pickle.dumps(value)).decode()

db=SqliteDatabase("data/db/"+os.environ.get('FLASK_BANK_DATABASE','flask_bank')+".db")

class BaseModel(Model):
	class Meta:
		database = db

class Account(BaseModel):
	id_			 =	CharField(8)
	password	 =	CharField()
	account_data =	ObjectField()
	permisos	 =	BooleanField(default=False)
	saldo		 =	IntegerField(default=0)
	nmonedas	 =	IntegerField(default=0)

class Moneda(BaseModel):
	id_			=	CharField(13)
	valor		=	IntegerField()
	duracion	=	IntegerField()
	emision		=	IntegerField()
	id_account	=	ForeignKeyField(Account,to_field=Account.id_,related_name='monedas')

#El modelo del banco
class TBanco:
	def __init__(self,db_name):
		self.__clave_secreta=tools.randomString(16)
		self.__db_name=db_name
		global db
		db.connect()
		db.create_table(Account,safe=True)
		db.create_table(Moneda,safe=True)

	def getClaveSecreta(self):
		return self.__clave_secreta

	#Funciones para el usuario, basicas
	def crearCuenta(self,clave):
		global db
		db=SqliteDatabase("data/db/"+self.__db_name+".db")
		db.connect()
		if clave==self.__clave_secreta:
			#Si su clave es igual a la clave del banco le damos permisos a esa cuenta
			cuenta=TCuentaAdmin(clave,tools.randomString(8))
			cuenta._TCuenta__monedero = Monedero(cuenta,self.__db_name)
			#... y le agregamos 150 monedas con valores aleatorios dentro de un rango algo alto
			def agregarMonedas():
				for _ in xrange(75):
					cuenta.agregarMoneda(TMoneda([100,1000,10000][tools.random.randint(0,2)],tools.random.randint(720,2160)))
					cuenta.agregarMoneda(TMoneda([1,10][tools.random.randint(0,1)],tools.random.randint(1600,16000)))
		else:
			#Si su clave no es la del banco, creamos una cuenta normal (sin permisos)
			cuenta=TCuenta(clave,tools.randomString(8))
			cuenta._TCuenta__monedero = Monedero(cuenta,self.__db_name)
			#... y le agregamos 20 monedas con valor de 100 y duracion de 24 horas
			def agregarMonedas():
				for _ in xrange(20):
					cuenta.agregarMoneda(TMoneda(100,1440))
		#Creamos un registro con la cuenta que acabamos de crear
		registro=Account(id_=cuenta.getID(),account_data=cuenta,password=clave,permisos=cuenta.permisos())
		registro.save()
		#Cerramos los flujos de datos o conexiones con la base de datos y retornamos el ID de la cuenta
		threading.Thread(target=agregarMonedas).start()
		return cuenta.getID()

	def obtenerCuenta(self,ID,clave="_",admin=None):
		global db
		db=SqliteDatabase("data/db/"+self.__db_name+".db")
		db.connect()
		cursor=Account.select(Account.id_,Account.password).where(Account.id_ == ID)
		if cursor.count():
			password=next(cursor.__iter__()).password
			if password==clave:
				cuenta=next(Account.select(Account.account_data,Account.id_).where(Account.id_ == ID).__iter__()).account_data
				cuenta.actualizarSaldo()
				info = next(Account.select(Account.saldo,Account.nmonedas).where(Account.id_ == ID).__iter__())
				return {
					"cuenta":cuenta,
					"saldo":info.saldo,
					"monedas":info.nmonedas
				}
			elif admin and admin.permisos():
				cuenta=next(Account.select(Account.account_data).where(Account.id_ == ID).__iter__()).account_data
				cuenta.actualizarSaldo()
				info = next(Account.select(Account.saldo,Account.nmonedas).where(Account.id_ == ID).__iter__())
				return {
					"cuenta":cuenta,
					"saldo":info.saldo,
					"monedas":info.nmonedas
				}
			else:
				return False
		else:
			return None

	def obtenerCuentas(self,admin,page=1,pagesize=20):
		global db
		db=SqliteDatabase("data/db/"+self.__db_name+".db")
		db.connect()
		#Verificamos que la cuenta que quiere acceder a esta informacion tenga permisos
		if admin.permisos():
			if page<=0:
				return {"error":True,"error_message":"Pagina "+str(page)+" fuera de rango"}
			cursor=Account.select(Account.id_,Account.password,Account.saldo,Account.nmonedas).offset(pagesize*(page-1))
			if not(cursor.count()):
				return {"error":True,"error_message":"Pagina "+str(page)+" fuera de rango"}
			cuentas=[cuenta.__dict__['_data'] for cuenta in cursor.peek(pagesize)]
			last_page=False
			if len(cuentas)<pagesize or cursor.count()==pagesize:
				last_page=True
			return {
				"error":False,
				"cuentas":cuentas,
				"page":page,
				"last_page":last_page
			}
		else:
			return {"error":True,"error_message":"Permiso denegado"}

class Monedero:
	"""docstring for Monedero"""
	def __init__(self,cuenta,db_name):
		self.__cuenta=cuenta
		self.__db_name=db_name

	def __call__(self,a_funcion):
		def actualizarMonedas():
			global db
			db=SqliteDatabase("data/db/"+self.__db_name+".db")
			db.connect()
			self.__cuenta.saldo_valor=sum(
				[
					moneda.valor for moneda in Moneda.select(Moneda,Account).join(Account).where(
						(Account.id_ == self.__cuenta.getID()) & (Moneda.emision+(Moneda.duracion*60)>time.time())
					)
				]
			)
			monedas = Moneda.select().join(Account).where(
				(Account.id_ == self.__cuenta.getID()) & (Moneda.emision+(Moneda.duracion*60)>time.time())
			)
			self.__cuenta.saldo_monedas=self.mapCurToTMonedas(monedas)
			r=a_funcion()
			del self.__cuenta.saldo_monedas
			del self.__cuenta.saldo_valor
			if self.__cuenta.cambio["cambio"]:
				if self.__cuenta.cambio["tipo"]=="nueva_moneda":
					moneda = Moneda(
						id_			=	self.__cuenta.cambio['moneda']['ID'],
						valor		=	self.__cuenta.cambio['moneda']['valor'],
						emision		=	self.__cuenta.cambio['moneda']['emision'],
						duracion	=	self.__cuenta.cambio['moneda']['duracion'],
						id_account	=	self.__cuenta.getID()
					)
					moneda.save()
				elif self.__cuenta.cambio["tipo"]=="transferencia":
					moneda = next(Moneda.select(Moneda.id_,Moneda.id_account).where(
						Moneda.id_ == self.__cuenta.cambio['id_moneda']
						).__iter__()
					)
					moneda.id_account = self.__cuenta.cambio['cuenta']
					moneda.save()
				elif self.__cuenta.cambio["tipo"]=="nueva_password":
					cuenta = next(Account.select(Account.id_,Account.password).where(
						Account.id_ == self.__cuenta.getID()
						).__iter__()
					)
					cuenta.password = self.__cuenta.cambio['nueva_password']
					cuenta.save()
			del self.__cuenta.cambio
			return r
		return actualizarMonedas

	def actualizador(self,a_funcion):
		def actualizar():
			a_funcion()
			global db
			db=SqliteDatabase("data/db/"+self.__db_name+".db")
			db.connect()
			cuenta = next(Account.select().where(Account.id_ == self.__cuenta.getID()).__iter__())
			cuenta.nmonedas = Moneda.select(Moneda,Account).join(Account).where(
				(Account.id_ == self.__cuenta.getID()) & (Moneda.emision+(Moneda.duracion*60)>time.time())
			).count()
			cuenta.saldo = sum(
				[
					moneda.valor for moneda in Moneda.select(
						Moneda.valor,Moneda.emision,Moneda.duracion,Account.id_
					).join(Account).where(
						Account.id_ == self.__cuenta.getID() & Moneda.emision+(Moneda.duracion*60)>time.time()
					)
				]
			)
			cuenta.save()
		return actualizar

	def obtenerMonedasEnRango(self,rango,tipo_filtro):		
		#Modificar
		return []

	def mapCurToTMonedas(self,cursor):
		return list(
			map(
				lambda moneda:TMoneda(
					ID		 =	moneda.id_,
					valor	 =	moneda.valor,
					duracion =	moneda.duracion,
					emision	 =	moneda.emision
				), 
				cursor
			)
		)

class TMoneda:
	def __init__(self,valor,duracion,emision=None,ID=None):
		if emision and ID:
			self.__id=ID
			self.__emision=emision
			self.__duracion=duracion
			self.__valor=valor
		else:
			self.__id=tools.randomString(13)
			self.__emision=time.time()
			self.__duracion=duracion
			self.__valor=valor
		if not((self.__valor in [1,10,100,1000,10000]) and (self.__duracion>=10 and self.__duracion<=16000)):
			raise Exception("Datos de la moneda invalidos")

	def consultarExpiracion(self):
		return self.__duracion-self.tiempoActiva()

	def tiempoActiva(self):
		return int((time.time()/60)-(self.__emision/60))

	def consultarValor(self):
		return self.__valor
	
	def getID(self):
		return self.__id

	def __json__(self):
		return {
			"ID":self.getID(),
			"valor":self.consultarValor(),
			"expiracion":self.consultarExpiracion(),
			"tiempo_activa":self.tiempoActiva(),
			"emision":self.__emision,
			"duracion":self.__duracion
		}

class TCuenta:
	def __init__(self,clave,ID):
		self.__id=ID
		self.__password=clave

	def getID(self):
		return self.__id

	#Funciones de consulta de saldo y modificacion de saldo

	def getSaldo(self,que="_"):
		@self.__monedero
		def f():
			self.cambio={"cambio":False}
			if que.lower()=="valor":
				return self.saldo_valor
			elif que.lower()=="monedas":
				return self.saldo_monedas
			else:
				return {
					"valor":self.saldo_valor,
					"monedas":self.saldo_monedas
				}
		return f()

	def getMoneda(self,ID):
		@self.__monedero
		def f():
			self.cambio={"cambio":False}
			for moneda in self.saldo_monedas:
				if moneda.getID()==ID:
					return moneda
		return f()

	def agregarMoneda(self,moneda):
		@self.__monedero
		def f(moneda=moneda):
			if moneda.consultarValor()>0 and moneda.consultarExpiracion()>0:
				self.cambio={"cambio":True,"tipo":"nueva_moneda","moneda":moneda.__json__()}
				return True
			else:
				self.cambio={"cambio":False}
				return False
		return f()

	#Deberia renombrarla a 'actualizarCuenta'
	def actualizarSaldo(self):
		@self.__monedero.actualizador
		def actualizar():
			pass
		threading.Thread(target=actualizar).start()
	
	#--rango = tupla (int limite_inferior,int limite_superior) - (si el limite_inferior es mayor que el limite_superior entonces
	#se retornaran todas las monedas que no esten dentro del rango (limite_superior,limite_inferior))
	#--tipo_filtro = string 'exp' (por expiracion), 'val' (por valor)
	def obtenerMonedasEnRango(self,rango,tipo_filtro):
		return self.__monedero.obtenerMonedasEnRango(rango,tipo_filtro)

	def seleccionarMonedasPorID(self,ids):
		@self.__monedero
		def f():
			self.cambio={"cambio":False}
			return list(filter(lambda moneda:(moneda.getID() in ids),self.saldo_monedas))
		return f()

	#Funcion de transferencia

	def transferirMoneda(self,moneda,cuenta):
		@self.__monedero
		def f():
			try:
				self.cambio={"cambio":True,"tipo":"transferencia","id_moneda":moneda.getID(),"cuenta":cuenta.getID()}
			except:
				self.cambio={"cambio":True,"tipo":"transferencia","id_moneda":moneda.getID(),"cuenta":cuenta}
		f()
	
	def transferirMonedas(self,monedas,cuenta):
		for moneda in monedas:
			self.transferirMoneda(moneda,cuenta)

	#Funciones de confirmacion y cambio de clave/password

	def confirmarClave(self,password):
		return self.__password==password

	def cambiarClave(self,old_pass,new_pass):
		@self.__monedero
		def f():
			if confirmarClave(old_pass):
				self.cambio={"cambio":True,"tipo":"nueva_password","nueva_password":new_pass}
				self.__password=new_pass
				return True
			else:
				self.cambio={"cambio":False}
				return False
		return f()

	#Metodo para comprobar sus permisos

	def permisos(self):
		return False

	#JSON

	def __json__(self):
		return {
			"ID":self.getID(),
			"saldo_valor":self.getSaldo("valor"),
			"saldo_monedas":[moneda.__json__() for moneda in self.getSaldo("monedas")]
		}

class TCuentaAdmin(TCuenta):
	def __init__(self,clave,ID):
		self._TCuenta__password=clave
		self._TCuenta__id=ID

	def permisos(self):
		return True

#Funciones de utilidades

#	TCambio, recibe una lista de monedas y segun modo y valor retorna otra lista de monedas
#monedas:	lista de monedas a cambiar
#modo:		div o mul, si por el valor que tienen las monedas se obtendran 
#			menos monedas con mas 'valor' respecto a evaluar o mas monedas con menos valor 
#evaluar: 	si las monedas que se quieren cambiar se tienen que evaluar por su expiracion o su valor
def TCambio(monedas,modo,evaluar):
	new_monedas=[]
	if modo=="div":
		if evaluar=="exp":
			pass
		elif evaluar=="val":
			pass
	elif modo=="mul":
		if evaluar=="exp":
			pass
		elif evaluar=="val":
			pass
	elif modo=="tra":
		if evaluar=="exp":
			pass
		elif evaluar=="val":
			pass
	return new_monedas

def paginarMonedas(cuenta,page,pagesize=20):
	if page<=0:
		return {"error":True,"error_message":"Pagina "+str(page)+" fuera de rango"}
	elif (page-1)*pagesize>len(cuenta.getSaldo('monedas')):
		return {"error":True,"error_message":"Pagina "+str(page)+" fuera de rango"}
	else:
		if (page)*pagesize>=len(cuenta.getSaldo('monedas')):
			return {
				"error":False,
				"last_page":True,
				"monedas":cuenta.getSaldo("monedas")[((page-1)*20):]
			}
		else:
			return {
				"error":False,
				"last_page":False,
				"monedas":cuenta.getSaldo("monedas")[((page-1)*20):((page)*20)]
			}

#Luis Albizo 2016-12-29
