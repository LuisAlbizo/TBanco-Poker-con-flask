import time, pickle, base64, threading, os
from pymongo import MongoClient
from functools import reduce
import tools.tools as tools

def EncodeObject(obj):
	return base64.b64encode(pickle.dumps(obj)).decode()

def DecodeObject(data):
	return pickle.loads(base64.b64decode(data.encode()))

class TBanco:
	def __init__(self,db_name):
		self.__clave_secreta=tools.randomString(16)
		self.__db_name=db_name

	def getClaveSecreta(self):
		return self.__clave_secreta

	#Funciones para el usuario, basicas
	def crearCuenta(self,clave):
		conn = MongoClient('127.0.0.1',27017)
		db=conn.get_database(self.__db_name)
		if clave==self.__clave_secreta:
			#Si su clave es igual a la clave del banco le damos permisos a esa cuenta
			cuenta=TCuentaAdmin(clave,tools.randomString(8))
			cuenta._TCuenta__monedero = Monedero(cuenta,self.__db_name)
			#... y le agregamos 150 monedas con valores aleatorios dentro de un rango algo alto
			def agregarMonedas():
				for _ in xrange(75):
					cuenta.agregarMoneda(TMoneda([100,1000,10000][tools.random.randint(1,2)],tools.random.randint(720,2160)))
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
		db.accounts.insert({
			"id_"			:	cuenta.getID(),
			"account_data"	:	EncodeObject(cuenta),
			"password"		:	clave,
			"permisos"		:	cuenta.permisos()
		})
		#Cerramos los flujos de datos o conexiones con la base de datos y retornamos el ID de la cuenta
		conn.close()
		threading.Thread(target=agregarMonedas).start()
		return cuenta.getID()

	def obtenerCuenta(self,ID,clave="_",admin=None):
		conn = MongoClient('127.0.0.1',27017)
		db=conn.get_database(self.__db_name)
		cursor=db.accounts.find({'id_' : ID},{'password':1,'account_data':1})
		if cursor.count():
			match = cursor.next()
			conn.close()
			password = match['password']
			if password==clave:
				cuenta=DecodeObject(match['account_data'])
				return {
					"cuenta":cuenta,
					"saldo":cuenta.getSaldo('valor'),
					"monedas":len(cuenta.getSaldo('monedas'))
				}
			elif admin and admin.permisos():
				cuenta=DecodeObject(match['account_data'])
				return {
					"cuenta":cuenta,
					"saldo":cuenta.getSaldo('valor'),
					"monedas":len(cuenta.getSaldo('monedas'))
				}
			else:
				return False
		else:
			return None

	def obtenerCuentas(self,admin,page=1,pagesize=20):
		#Verificamos que la cuenta que quiere acceder a esta informacion tenga permisos
		if admin.permisos():
			if page<=0:
				return {"error":True,"error_message":"Pagina "+str(page)+" fuera de rango"}
			conn = MongoClient('127.0.0.1',27017)
			db=conn.get_database(self.__db_name)
			cursor = db.accounts.find().skip((page-1)*pagesize)
			if not(cursor.count()):
				conn.close()
				return {"error":True,"error_message":"Pagina "+str(page)+" fuera de rango"}
			cuentas=[cuenta for cuenta in cursor.limit(pagesize)]
			last_page=False
			if len(cuentas)<pagesize or cursor.count()==pagesize:
				last_page=True
			conn.close()
			return {
				"error"		:	False,
				"cuentas"	:	cuentas,
				"page"		:	page,
				"last_page"	:	last_page
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
			conn = MongoClient('127.0.0.1',27017)
			db=conn.get_database(self.__db_name)
			monedas = list(filter(lambda x : (x['emision']+(x['duracion']*60)>time.time()),db.monedas.find({
				'id_account':self.__cuenta.getID()
			})))
			self.__cuenta.saldo_valor=sum([moneda['valor'] for moneda in monedas])
			self.__cuenta.saldo_monedas=[DecodeObject(moneda['moneda_data']) for moneda in monedas]
			r=a_funcion()
			del self.__cuenta.saldo_monedas
			del self.__cuenta.saldo_valor
			if self.__cuenta.cambio["cambio"]:
				if self.__cuenta.cambio["tipo"]=="nueva_moneda":
					db.monedas.insert({
						'id_'		  :	self.__cuenta.cambio["moneda"].getID(),
						'id_account'  :	self.__cuenta.getID(),
						'moneda_data' :	EncodeObject(self.__cuenta.cambio["moneda"]),
						'emision'	  : self.__cuenta.cambio["moneda"].__json__()['emision'],
						'duracion'	  : self.__cuenta.cambio["moneda"].__json__()['duracion'],
						'valor'		  : self.__cuenta.cambio["moneda"].consultarValor()
					})
				elif self.__cuenta.cambio["tipo"]=="transferencia":
					db.monedas.update({'id_':self.__cuenta.cambio["id_moneda"]},{'$set':{'id_account':self.__cuenta.getID()}})
				elif self.__cuenta.cambio["tipo"]=="nueva_password":
					db.accounts.update({'id_':self.__cuenta.getID()},{'$set':{'password':self.__cuenta.cambio["password"]}})
			del self.__cuenta.cambio
			conn.close()
			return r
		return actualizarMonedas
	
	def obtenerMonedasEnRango(self,rango,tipo_filtro):		
		#Modificar
		return []

class TMoneda:
	def __init__(self,valor,duracion):
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
		def f():
			self.cambio={"cambio":True,"tipo":"nueva_moneda","moneda":moneda}
		return f()

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
