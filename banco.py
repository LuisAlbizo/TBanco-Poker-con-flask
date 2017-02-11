import time, pickle, base64, sqlite3, threading
from functools import reduce
import tools.tools as tools

class TBanco:
	def __init__(self,cuentas_db):
		self.__clave_secreta=tools.randomString(16)
		self.__cuentas_db=cuentas_db
		db_accounts=sqlite3.connect("./data/db/"+self.__cuentas_db+".db")
		db_accounts.execute(
		"CREATE TABLE IF NOT EXISTS Accounts(ID VARCHAR(8) NOT NULL,Account_data TEXT NOT NULL,password TEXT NOT NULL,\
		Saldo INTEGER,permisos BOOLEAN NOT NULL,monedas INTEGER)")
		db_accounts.execute("CREATE TABLE IF NOT EXISTS AccountsCount(ID INTEGER NOT NULL,Count INTEGER)")
		db_accounts.execute("CREATE TABLE IF NOT EXISTS Monedas(ID VARCHAR(13) NOT NULL, valor INTEGER NOT NULL,\
		creacion INTEGER NOT NULL, duracion INTEGER NOT NULL, ID_Account VARCHAR(8) NOT NULL)")
		try:
			next(db_accounts.execute("SELECT * FROM AccountsCount"))
		except:
			db_accounts.execute("INSERT INTO AccountsCount (ID,Count) VALUES (0,0)")
		db_accounts.commit()
		db_accounts.close()

	def getClaveSecreta(self):
		return self.__clave_secreta

	#Funciones para el usuario, basicas

	def crearCuenta(self,clave):
		if clave==self.__clave_secreta:
			#Si su clave es igual a la clave del banco le damos permisos a esa cuenta
			cuenta=TCuentaAdmin(clave,tools.randomString(8))
			cuenta._TCuenta__monedero = Monedero(cuenta,self.__cuentas_db)
			#... y le agregamos 150 monedas con valores aleatorios dentro de un rango algo alto
			def agregarMonedas():
				for _ in range(75):
					cuenta.agregarMoneda(TMoneda([100,1000,10000][tools.random.randint(0,2)],tools.random.randint(720,2160)))
					cuenta.agregarMoneda(TMoneda([1,10][tools.random.randint(0,1)],tools.random.randint(1600,16000)))
			threading.Thread(target=agregarMonedas).start()
		else:
			#Si su clave no es la del banco, creamos una cuenta normal (sin permisos)
			cuenta=TCuenta(clave,tools.randomString(8))
			cuenta._TCuenta__monedero = Monedero(cuenta,self.__cuentas_db)
			#... y le agregamos 20 monedas con valor de 100 y duracion de 24 horas
			def agregarMonedas():
				for _ in range(20):
					cuenta.agregarMoneda(TMoneda(100,1440))
			threading.Thread(target=agregarMonedas).start()
		#Establecemos la conexion a la base de datos
		db_accounts=sqlite3.connect("./data/db/"+self.__cuentas_db+".db")
		#Creamos un registro con la cuenta que acabamos de crear
		db_accounts.execute(
			"INSERT INTO 'Accounts' (ID,Account_data,password,permisos) VALUES ('%s','%s','%s','%s')" % (
				cuenta.getID(), base64.b64encode(pickle.dumps(cuenta)).decode(), clave, cuenta.permisos()
				)
			)
		#Aumentamos el contador de cuentas dentro de la base de datos en 1
		db_accounts.execute("UPDATE AccountsCount SET Count=Count+1 WHERE ID=0")
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
				print(info)
				print(next(db_accounts.execute("SELECT * FROM 'Accounts' WHERE ID='%s'" % ID)))
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

class Monedero:
	"""docstring for Monedero"""
	def __init__(self,cuenta,db_name):
		self.__cuenta=cuenta
		self.__db_name=db_name

	def __call__(self,a_funcion):
		def actualizarMonedas():
			db_accounts=sqlite3.connect("./data/db/"+self.__db_name+".db")
			self.__cuenta.saldo_valor=next(db_accounts.execute(
				"SELECT SUM(valor) FROM Monedas WHERE ID_Account='%s' AND ROUND((creacion/60)+duracion) > %i" % (
						self.__cuenta.getID(),
						int(time.time()/60)
					)
				)
			)[0]
			monedas = db_accounts.execute(
				"SELECT ID,valor,duracion,creacion,ROUND((creacion/60)+duracion) AS expiracion  FROM Monedas WHERE\
				ID_Account='%s' AND expiracion > %i" % (
					self.__cuenta.getID(),
					int(time.time()/60)
				)
			)
			self.__cuenta.saldo_monedas=self.mapCurToTMonedas(monedas)
			r=a_funcion()
			if r=="actualizacion":
				db_accounts.close()
				return True
			del self.__cuenta.saldo_monedas
			del self.__cuenta.saldo_valor
			if self.__cuenta.cambio["cambio"]:
				if self.__cuenta.cambio["tipo"]=="nueva_moneda":
					db_accounts.execute("INSERT INTO Monedas VALUES('%s',%i,%i,%i,'%s')" % (
						self.__cuenta.cambio['moneda']['ID'],
						self.__cuenta.cambio['moneda']['valor'],
						self.__cuenta.cambio['moneda']['emision'],
						self.__cuenta.cambio['moneda']['duracion'],
						self.__cuenta.getID()
						)
					)
				elif self.__cuenta.cambio["tipo"]=="transferencia":
					db_accounts.execute("UPDATE Monedas SET ID_Account='%s' WHERE ID='%s'" % (
						self.__cuenta.getID(),
						self.__cuenta.cambio['id_moneda']
						)
					)
				elif self.__cuenta.cambio["tipo"]=="nueva_password":
					db_accounts.execute("UPDATE Accounts SET password='%s' WHERE ID='%s'" % (
						self.__cuenta.cambio['nueva_password'],
						self.__cuenta.getID()
						)
					)
				db_accounts.commit()
			del self.__cuenta.cambio
			db_accounts.close()
			return r
		return actualizarMonedas

	def actualizador(self,a_funcion):
		def actualizar():
			a_funcion()
			db_accounts=sqlite3.connect("./data/db/"+self.__db_name+".db")
			db_accounts.execute(
				"UPDATE Accounts SET monedas=%i, saldo=%i, Account_data='%s' WHERE ID='%s' AND ROUND((creacion/60)+duracion) > %i" % (
					self.__cuenta.getID(),
					next(db_accounts.execute("SELECT COUNT(*) FROM Monedas WHERE ID_Account='%s'"))[0],
					self.__cuenta.getID(),
					next(db_accounts.execute("SELECT SUM(valor) FROM Monedas WHERE ID_Account='%s'"))[0],
					base64.b64encode(pickle.dumps(self.__cuenta)).decode(),
					self.__cuenta.getID(),
					int(time.time()/60)
				)
			)
			db_accounts.commit()
			db_accounts.close()
		return a_funcion

	def obtenerMonedasEnRango(self,rango,tipo_filtro):		
		db_accounts=sqlite3.connect("./data/db/"+self.__db_name+".db")
		if rango[0]>rango[1]:
			if tipo_filtro=="exp":
				matches=self.mapCurToTMonedas(
					db_accounts.execute(
						"SELECT ID,valor,duracion,creacion,ROUND((creacion/60)+duracion) AS expiracion FROM Monedas WHERE\
						ID_Account='%s' AND expiracion > %i AND ((expiracion >= 0 AND expiracion <= %i) OR\
						(expiracion >= %i AND expiracion <= 16000))" % (
							self.__cuenta.getID(),
							int(time.time()/60),
							rango[1],
							rango[0]
						)
					)
				)
				db_accounts.close()
				return matches
			if tipo_filtro=="val":
				matches=self.mapCurToTMonedas(
					db_accounts.execute(
						"SELECT ID,valor,duracion,creacion,ROUND((creacion/60)+duracion) AS expiracion FROM Monedas WHERE\
						ID_Account='%s' AND expiracion > %i AND ((valor >= 0 AND valor <= %i) OR\
						(valor >= %i AND valor <= 16000))" % (
							self.__cuenta.getID(),
							int(time.time()/60),
							rango[1],
							rango[0]
						)
					)
				)
				db_accounts.close()
				return matches
		else:
			if tipo_filtro=="exp":
				matches=self.mapCurToTMonedas(
					db_accounts.execute(
						"SELECT ID,valor,duracion,creacion,ROUND((creacion/60)+duracion) AS expiracion FROM Monedas WHERE\
						ID_Account='%s' AND expiracion > %i AND expiracion >= %i AND expiracion <= %i" % (
							self.__cuenta.getID(),
							int(time.time()/60),
							rango[0],
							rango[1]
						)
					)
				)
				db_accounts.close()
				return matches
			elif tipo_filtro=="val":
				matches=self.mapCurToTMonedas(
					db_accounts.execute(
						"SELECT ID,valor,duracion,creacion,ROUND((creacion/60)+duracion) AS expiracion FROM Monedas WHERE\
						ID_Account='%s' AND expiracion > %i AND valor >= %i AND valor <= %i" % (
							self.__cuenta.getID(),
							int(time.time()/60),
							rango[0],
							rango[1]
						)
					)
				)
				db_accounts.close()
				return matches

	def mapCurToTMonedas(self,cursor):
		return list(
			map(
				lambda monedaTupla:TMoneda(
						ID=monedaTupla[0],
						valor=monedaTupla[1],
						duracion=monedaTupla[2],
						emision=monedaTupla[3]
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
				del moneda
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
