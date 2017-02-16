import re, random, itertools
from functools import reduce
from cartas import *

def carta2str(carta):
	return carta['valor'] + carta['color'][0]

def mano2str(mano):
	return reduce(lambda a,b:a+"-"+b,[carta2str(carta) for carta in mano])

def str2carta(carta_str):
	return {'color':next(filter(lambda x:x[0]==carta_str[1],cartas['colores'])),'valor':carta_str[0]}

def str2mano(mano_str):
	return [str2carta(carta) for carta in mano_str.split("-")]

#Funcion para repartir

def repartir(njugadores):
	maso = [c for c in cartas['maso']]
	p = {'repartidas':[],'flop':[],'turn':None,'river':None}
	mano=[]
	for _ in range(njugadores):
		for __ in range(2):
			carta = random.choice(maso)
			maso.remove(carta)
			mano.append(carta)
		p['repartidas'].append(mano)
		mano=[]
	for _ in range(3):
		carta = random.choice(maso)
		maso.remove(carta)
		p['flop'].append(carta)
	carta = random.choice(maso)
	maso.remove(carta)
	p['turn'] = carta
	carta = random.choice(maso)
	maso.remove(carta)
	p['river'] = carta
	return p

#Funciones de Evaluacion

def alta(mano):
	return {'val':0,'top':max([cartas['valores'].index(c['valor']) for c in mano])}

def par(mano):
	r={'val':0,'top':-1}
	for _ in range(len(cartas['valores'])):
		if mano2str(mano).count(cartas['valores'][_])==2:
			r['top']=_
			if r['val']<2:
				r['val']+=1
			else:
				return r
	return r

def trio(mano):
	r={'val':0,'top':-1}
	for _ in range(len(cartas['valores'])):
		if mano2str(mano).count(cartas['valores'][_])==3:
			r['top']=_
			r['val']=3
	return r

def escalera(mano):
	r={'val':0,'top':-1}
	valores='A23456789DJQKA'
	for _ in range(10):
		if set([c["valor"] for c in mano]).issuperset(set(valores[_:_+5])):
			r['val']=4
			r['top']=_+4
	return r

def color(mano):
	r={'val':0,'top':-1}
	for _ in range(len(cartas['colores'])):
		if mano2str(mano).count(cartas['colores'][_][0])>=5:
			for c in mano:
				if c['color']==cartas['colores'][_] and cartas['valores'].index(c['valor'])>r['top']:
					r['top']=cartas['valores'].index(c['valor'])
			r['val']=5
			return r
	return r

def fullhouse(mano):
	r={'val':0,'top':-1,'tok':-1}
	t=trio(mano)
	if t['val']:
		p=par([c for c in mano if c['valor']!=cartas['valores'][t['top']]])
		if p['val']:
			r['val']=6
			r['top']=max([p['top'],t['top']])
			r['tok']=min([p['top'],t['top']])
	return r

def poker(mano):
	r={'val':0,'top':-1}
	for _ in range(len(cartas['valores'])):
		if mano2str(mano).count(cartas['valores'][_])==4:
			r['top']=_
			r['val']=7
			break
	return r

def escalera_color(mano):
	r={'val':0,'top':-1}
	valores='A23456789DJQKA'
	colores='CDET'
	for _ in range(10):
		for __ in colores:
			esc=set([carta for carta in [v+__ for v in valores][_:_+5]])
			if esc.issubset(set([carta2str for carta in mano])):
				r['val']=8
				r['top']=_+4
	return r

def escalera_real(mano):
	r={'val':0,'top':-1}
	ec=escalera_color(mano)
	if ec['val'] and ec['top']==13:
		r['val']=9
		r['top']=13
	return r

#

def evaluar_mano(mano):
	for _ in [escalera_real,escalera_color,poker,fullhouse,color,escalera,trio,par]:
		ev=_(mano)
		if ev['val']:
			if 'tok' in ev:
				return (ev['val']*100)+ev['top']+ev['tok']
			else:
				return (ev['val']*100)+ev['top']
	return alta(mano)['top']

#

def evaluar_ganador(jugadores,comunitarias):
	#jugadores = [{ id : 1, mano : [{...},{...}] }, { id : 2, mano : [{...},{...}] },...]
	#comunitarias = [{...}, {...}, {...}, {...}, {...} ]
	ganadores=[]
	wins=max([evaluar_mano(mano+comunitarias) for mano in [j['mano'] for j in jugadores]])
	for el in jugadores:
		if evaluar_mano(el['mano'])==wins:
			ganadores.append(el['id'])
	t={
		'0'	:	'Carta Alta',
		'1'	:	'Par',
		'2'	:	'Doble Par',
		'3'	:	'Trio',
		'4'	:	'Escalera',
		'5'	:	'Color',
		'6'	:	'Full House',
		'7'	:	'Poker',
		'8'	:	'Escalera de Color',
		'9'	:	'Escalera Imperial'
	}[(lambda x:str(x)[0] if len(str(x))==3 else '0')(wins)]
	return {'ganadores':ganadores,'wins':t}

def simular():
	r=repartir(6)
	com=r['flop']+[r['river'],r['turn']]
	j=[]
	for i in range(6):
		j.append({'id':i,'mano':r['repartidas'][i]})
	return {'j':j,'com':com,'p':evaluar_ganador(j,com)}

#Luis Albizo 2017-02-16
