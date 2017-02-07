import time,pickle,base64,sqlite3
from functools import reduce
import tools.tools as tools

class TBanco:
	def __init__(self,cuentas_db):
		self.__clave_secreta=tools.randomString(16)
		self.__cuentas_db=cuentas_db
		db_accounts=sqlite3.connect("./data/db/"+self.__cuentas_db+".db")
		db_accounts.execute(
		"CREATE TABLE IF NOT EXISTS Accounts(ID TEXT NOT NULL,Account_data TEXT NOT NULL,password TEXT NOT NULL,Saldo INTEGER,permisos BOOLEAN NOT NULL,monedas INTEGER)")
		db_accounts.execute("CREATE TABLE IF NOT EXISTS AccountsCount(ID INTEGER NOT NULL,Count INTEGER)")
		try:
			next(db_accounts.execute("SELECT * FROM AccountsCount"))
		except:
			db_accounts.execute("INSERT INTO 'AccountsCount' (ID,Count) VALUES (0,0)")
		db_accounts.commit()
		db_accounts.close()

	def getClaveSecreta(self):
		return self.__clave_secreta

	#Funciones para el usuario, basicas

	def crearCuenta(self,clave):
		if clave==self.__clave_secreta:
			#Si su clave es igual a la clave del banco le damos permisos a esa cuenta
			cuenta=TCuentaAdmin(clave,tools.randomString(8))
			cuenta._TCuenta__actualizadora = Actualizadora(cuenta,self.__cuentas_db)
			#... y le agregamos 150 monedas con valores aleatorios dentro de un rango algo alto
			for _ in range(75):
				cuenta.agregarMoneda(TMoneda([100,1000,10000][tools.random.randint(0,2)],tools.random.randint(720,2160)))
				cuenta.agregarMoneda(TMoneda([1,10][tools.random.randint(0,1)],tools.random.randint(1600,16000)))
		else:
			#Si su clave no es la del banco, creamos una cuenta normal (sin permisos)
			cuenta=TCuenta(clave,tools.randomString(8))
			cuenta._TCuenta__actualizadora = Actualizadora(cuenta,self.__cuentas_db)
			#... y le agregamos 20 monedas con valor de 100 y duracion de 24 horas
			for _ in range(20):
				cuenta.agregarMoneda(TMoneda(100,1440))
		#Establecemos la conexion a la base de datos
		db_accounts=sqlite3.connect("./data/db/"+self.__cuentas_db+".db")
		#Creamos un registro con la cuenta que acabamos de crear
		db_accounts.execute(
			"INSERT INTO 'Accounts' (ID,Account_data,password,permisos) VALUES ('%s','%s','%s','%s')" % (
				cuenta.getID(), base64.b64encode(pickle.dumps(cuenta)).decode(), clave, cuenta.permisos()
				)
			)
		#Aumentamos el contador de cuentas dentro de la base de datos en 1
		db_accounts.execute(
			"UPDATE AccountsCount SET Count=%i WHERE ID=0" % (
				next(db_accounts.execute("SELECT Count FROM AccountsCount WHERE ID=0"))[0]
				)
			)
		#Cerramos los flujos de datos o conexiones con la base de datos y retornamos el ID de la cuenta
		db_accounts.commit()
		db_accounts.close()
		cuenta.actualizarSaldo()
		return cuenta.getID()

	def obtenerCuenta(self,ID,clave="_",admin=None):
		db_accounts=sqlite3.connect("./data/db/"+self.__cuentas_db+".db")
		cursor=db_accounts.execute("SELECT password FROM 'Accounts' WHERE ID='%s'" % ID)
		try:
			password=next(cursor)[0]
			cursor.close()
			if password==clave:
				info=next(db_accounts.execute("SELECT Account_data, saldo, monedas FROM 'Accounts' WHERE ID='%s'" % ID))
				db_accounts.close() 
				cuenta=pickle.loads(base64.b64decode(info[0].encode()))
				return {
					"cuenta":cuenta,
					"saldo":info[1],
					"monedas":info[2]
					}
			elif admin and admin.permisos():
				info=next(db_accounts.execute("SELECT Account_data, saldo, monedas FROM 'Accounts' WHERE ID='%s'" % ID))
				db_accounts.close()
				cuenta=pickle.loads(base64.b64decode(info[0].encode()))
				return {
					"cuenta":cuenta,
					"saldo":info[1],
					"monedas":info[2]
					}
			else:
				return False
		except:
			cursor.close()
			db_accounts.close()
			return None

	def obtenerCuentas(self,admin,datos=["id","password","saldo","monedas"],page=1,pagesize=20):
		#Verificamos que la cuenta que quiere acceder a esta informacion tenga permisos
		if admin.permisos():
			if page<=0:
				return {"error":True,"error_message":"Pagina "+str(page)+" fuera de rango"}
			db_accounts=sqlite3.connect("./data/db/"+self.__cuentas_db+".db")
			cursor=db_accounts.execute("select %s from 'Accounts'" % reduce(lambda a,b:a+","+b,datos))
			for _ in range(page-1):
				for __ in range(pagesize):
					try:
						next(cursor)
					except:
						return {"error":True,"error_message":"Pagina "+str(page)+" fuera de rango"}
			cuentas=[]
			last_page=False
			to_json=eval("lambda cuenta_cur:{%s}" % reduce(
					(lambda a,b:a+","+b),
					[("'%s':cuenta_cur[%i]" % (datos[i],i)) for i in range(len(datos))]
				)
			)
			for _ in range(pagesize):
				try:
					cuentas.append(to_json(next(cursor)))
				except:
					last_page=True
					break
			if not(last_page):
				try:
					next(cursor)
				except:
					last_page=True
			cursor.close()
			db_accounts.close()
			return {
				"error":False,
				"cuentas":cuentas,
				"page":page,
				"last_page":last_page
			}
		else:
			return {"error":True,"error_message":"Permiso denegado"}

class Actualizadora:
	"""docstring for Actualizadora"""
	def __init__(self,cuenta,db_name):
		self.__cuenta=cuenta
		self.__db_name=db_name
		
	def __call__(self,a_funcion):
		def actualizarCuenta():
			a_funcion()
			db_accounts=sqlite3.connect("./data/db/"+self.__db_name+".db")
			db_accounts.execute(
				"UPDATE Accounts SET Account_data='%s' WHERE ID='%s'" % (
					base64.b64encode(pickle.dumps(self.__cuenta)).decode(),
					self.__cuenta.getID()
				)
			)
			db_accounts.execute(
				"UPDATE Accounts SET Saldo=%i WHERE ID='%s'" % (
					self.__cuenta.getSaldo("valor"),
					self.__cuenta.getID()
				)
			)
			db_accounts.execute(
				"UPDATE Accounts SET monedas=%i WHERE ID='%s'" % (
					len(self.__cuenta.getSaldo("monedas")),
					self.__cuenta.getID()
				)
			)
			db_accounts.commit()
			db_accounts.close()
		return actualizarCuenta

class TMoneda:
	#valor puede ser 1 o 10 o 100 o 1000 o 10000
	#10<=duracion(minutos)<=16000
	def __init__(self,valor,duracion):
		self.__id=tools.randomString(5)
		self.__emision=int(time.time())
		self.__duracion=duracion
		self.__valor=valor
		if not((self.__valor in [1,10,100,1000,10000]) and (self.__duracion>=10 and self.__duracion<=16000)):
			raise Exception("Datos de la moneda invalidos")

	def consultarExpiracion(self):
		return int(self.__duracion)-self.tiempoActiva()

	def tiempoActiva(self):
		return int(time.time()/60)-int(self.__emision/60)

	def consultarValor(self):
		return self.__valor
	
	def getID(self):
		return self.__id

	def __json__(self):
		return {
			"ID":self.getID(),
			"valor":self.consultarValor(),
			"expiracion":self.consultarExpiracion(),
			"tiempo_activa":self.tiempoActiva()
		}

class TCuenta:
	def __init__(self,clave,ID):
		self.__saldo_valor=0
		self.__id=ID
		self.__saldo_monedas=[]
		self.__password=clave

	def getID(self):
		return self.__id

	#Funciones de consulta de saldo y modificacion de saldo

	def getSaldo(self,que="_"):
		if que.lower()=="valor":
			return self.__saldo_valor
		elif que.lower()=="monedas":
			return self.__saldo_monedas
		else:
			return {"valor":self.__saldo_valor,"monedas":self.__saldo_monedas}

	def getMoneda(self,ID):
		for moneda in self.__saldo_monedas:
			if moneda.getID()==ID:
				return moneda

	def agregarMoneda(self,moneda):
		if moneda.consultarValor()>0 and moneda.consultarExpiracion()>0:
			self.__saldo_monedas.append(moneda)
			self.actualizarSaldo()
			return True
		else:
			return False

	def actualizarSaldo(self):
		@self.__actualizadora
		def actualizar():
			self.__saldo_monedas = list(filter(lambda moneda:moneda.consultarExpiracion()>0,self.__saldo_monedas))
			self.__saldo_valor = sum([moneda.consultarValor() for moneda in self.__saldo_monedas])
		actualizar()

	#--rango = tupla (int limite_inferior,int limite_superior) - (si el limite_inferior es mayor que el limite_superior entonces
	#se retornaran todas las monedas que no esten dentro del rango (limite_superior,limite_inferior))
	#--tipo_filtro = string 'exp' (por expiracion), 'val' (por valor)
	def obtenerMonedasEnRango(self,rango,tipo_filtro):
		if rango[0]>rango[1]:
			return list(set(self.obtenerMonedasEnRango((0,rango[1]-1),tipo_filtro)).union(
			set(self.obtenerMonedasEnRango((rango[0]+1,16000),tipo_filtro))))
		else:
			if tipo_filtro=="exp":
				return list(set(filter(lambda moneda:moneda.consultarExpiracion()>=rango[0],self.__saldo_monedas)).intersection(
				set(filter(lambda moneda:moneda.consultarExpiracion()<=rango[1],self.__saldo_monedas))))
			elif tipo_filtro=="val":
				return list(set(filter(lambda moneda:moneda.consultarValor()>=rango[0],self.__saldo_monedas)).intersection(
				set(filter(lambda moneda:moneda.consultarValor()<=rango[1],self.__saldo_monedas))))

	def seleccionarMonedasPorID(self,ids):
		return list(filter(lambda moneda:(moneda.getID() in ids),self.__saldo_monedas))

	#Funcion de transferencia

	def transferirMonedas(self,monedas,cuenta):
		for moneda in monedas:
			cuenta.agregarMoneda(moneda)
			self.__saldo_monedas.remove(monedas)
		cuenta.actualizarSaldo()
		self.actualizarSaldo()

	#Funciones de confirmacion y cambio de clave/password

	def confirmarClave(self,password):
		return self.__password==password

	def cambiarClave(self,old_pass,new_pass):
		if confirmarClave(old_pass):
			self.__password=new_pass
			return True
		else:
			return False
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
		self._TCuenta__saldo_valor=0
		self._TCuenta__id=ID
		self._TCuenta__saldo_monedas=[]
		self._TCuenta__password=clave

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
