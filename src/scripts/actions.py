import re
from operator import itemgetter

#---------------------------------------------------------------------------
# Constants
#---------------------------------------------------------------------------

phases = [
    'It is currently in the Pre-game Setup Phase',
    "It is now {}'s READY Step",
    "It is now {}'s COMBAT Phase",
    "It is now {}'s ENDING Phase"]

AttackColor = "#ff0000"
BlockColor = "#ffff00"
DoesntUntapColor = "#ffffff"
NoDiffColor = "#0000ff"

MinusDamageMarker = ("-1 damage", "6f180a03-b3f5-4e6f-96b5-9ff1597d2226")
PlusDamageMarker = ("+1 damage", "6480e55b-0864-41bf-ad00-43cc2482a75c")
MinusSpeedMarker = ("-1 speed", "e7793480-7f5d-4863-adca-125b99049370")
PlusSpeedMarker = ("+1 speed", "c09409d2-ba3f-437c-a1b9-60a72613b091")

#---------------------------------------------------------------------------
# Global variables
#---------------------------------------------------------------------------

phaseIdx = 0
#cardsInPool = 0
#cardPool = []
#me.setGlobalVariable('cardPool','[ ]')
Turn = 0
tableside = None
isBlock = 0
handSize = 0
cardPoolPos = -300
cardPoolWidth = 70
cardSAWidth = 100
cardOverlap = 10
sideMultiplier = None
doAlignment = False
attachDict = {}

#---------------------------------------------------------------------------
# Table group actions
#---------------------------------------------------------------------------

def toggleAutoAlign(group, x = 0, y = 0):
	global doAlignment
	mute()
	doAlignment = not doAlignment
	if doAlignment:
		notify('{} turns Auto Align on.'.format(me))
	else:
		notify('{} turns Auto Align off.'.format(me))

def respond(group, x = 0, y = 0):
	notify('{} RESPONDS!'.format(me))

def passPriority(group, x = 0, y = 0):
	notify('{} passes priority to an opponent.'.format(me))

def passEnhance(group, x = 0, y = 0):
	notify('{} passes Enhance to an opponent.'.format(me))

def passturn(group):
	notify("{} has Ended his turn.".format(me))
	_realignCards()

def showCurrentPhase(group, x = 0, y = 0):
	notify(phases[phaseIdx].format(me))

def nextPhase(group, x = 0, y = 0):
	global phaseIdx
	phaseIdx += 1
	showCurrentPhase(group)
	_realignCards()

def goToReady(group, x = 0, y = 0):
	global phaseIdx
	phaseIdx = 1
	mute()
	myCards = (card for card in table
                    if card.controller == me
                    and card.highlight != DoesntUntapColor)
	for card in myCards: 
		card.orientation &= ~Rot90
	notify("{} untaps and enters the Combat Phase".format(me))
	_realignCards()

def goToCombat(group, x = 0, y = 0):
	global phaseIdx
	phaseIdx = 2
	showCurrentPhase(group)
	_realignCards()

def goToEnd(group, x = 0, y = 0):
	global phaseIdx
	phaseIdx = 3
	passturn(group)
	_realignCards()

def lose1Life(group, x = 0, y = 0):
	me.life -= 1

def gain1Life(group, x = 0, y = 0):
	me.life += 1

def scoop(group, x = 0, y = 0):
	mute()
	if not confirm("Are you sure you want to scoop?"): return
	me.life = 20
	myCards = (card for card in table
                    if card.controller == me
                    and card.owner == me)
	for card in myCards: 
		card.moveTo(me.Deck)
	for c in me.Discard: c.moveTo(me.Deck)
	for c in me.hand: c.moveTo(me.Deck)
	for c in me.piles['Removed From Game Zone']: c.moveTo(me.Deck)
	notify("{} scoops.".format(me))

def clearAll(group, x = 0, y = 0):
	notify("{} clears all targets.".format(me))
	for card in group:
		card.target(False)
		if card.controller == me and card.highlight in [AttackColor, BlockColor]:
			card.highlight = None

def roll6(group, x = 0, y = 0):
	mute()
	n = rnd(1, 6)
	notify("{} rolls {} on a 6-sided die.".format(me, n))

def roll20(group, x = 0, y = 0):
	mute()
	n = rnd(1, 20)
	notify("{} rolls {} on a 20-sided die.".format(me, n))

def flipCoin(group, x = 0, y = 0):
	mute()
	n = rnd(1, 2)
	if n == 1:
		notify("{} flips heads.".format(me))
	else:
		notify("{} flips tails.".format(me))

#---------------------------------------------------------------------------
# Table card actions
#---------------------------------------------------------------------------

def attach(card, x = 0, y = 0):
	global attachDict
	mute()
	target = [c for c in table if c.targetedBy]
	#targetcount = sum(1 for card in table if card.targetedBy() == me)
	if len(target) != 1:
		if len(target) == 0: notify('No targets to attach to')
		if len(target) > 1: notify('Too many targets on table')
		return
	targetcard = target[0]
	targetcard.target(False)
	if targetcard._id in attachDict:
		attachDict[targetcard._id].append(card._id)
	else:
		attachDict[targetcard._id] = [card._id]
	if re.search(r'character', targetcard.Type, re.I):
		card.moveToTable(targetcard.position[0] - cardOverlap * sideMultiplier, targetcard.position[1])
	else:
		card.moveToTable(targetcard.position[0] + cardOverlap * sideMultiplier, targetcard.position[1])
	card.sendToBack()
	notify('{} attached {} to {}.'.format(me, card, targetcard))
	

def _realignCards():
	global doAlignment, sideMultiplier, tableside, attachDict
	mute()
	cardPool = _getCardPool()
	_alignCardPool(cardPool)

	#Attachments... Dict/orphan cleanup phase
	newDict = {}
	for cid in attachDict.keys():
		card=Card(cid)
		if card not in table:
			for aid in attachDict[cid]:
				if Card(aid) in table:
					Card(aid).moveTo(me.Discard)
		if card in table and card not in cardPool:
			newDict[cid]=[]
			for aid in attachDict[cid]:
				if Card(aid) in table and Card(aid) not in cardPool:
					newDict[cid].append(aid)
	attachDict=newDict

	if not doAlignment: return # get the f out

	#Momentum
	momentum=[((card.position[0] * sideMultiplier), card) for card in table 
              if card.controller == me 
              and (card.position[0] * sideMultiplier) < (cardPoolPos - 25)
              and (card.position[1] * sideMultiplier) >= (tableside * sideMultiplier + 25)]
	momentum.sort(reverse=True)
	momentum=[card for pos, card in momentum]
	for counter, card in enumerate(momentum):
		card.moveToTable((cardPoolPos - cardPoolWidth - (cardOverlap * counter))  * sideMultiplier,tableside + (card.height() + 10) * sideMultiplier)
		card.sendToFront()

	#Staging Area
	saOrder = { 'foundation' : 0,
				'?'          : 1,
				'asset'      : 2 }
	attachedCards = [cid for subl in attachDict.values() for cid in subl]
	stagingArea=[(saOrder.get(card.Type.lower(), 1), card.Difficulty, card.Name, card) for card in table 
              if card.controller == me 
              and (card.position[0] * sideMultiplier) >= (cardPoolPos - 25)
              and (card.position[1] * sideMultiplier) >= (tableside * sideMultiplier + 25)
              and card._id not in attachedCards]
	stagingArea.sort(key=itemgetter(2))
	stagingArea.sort(key=itemgetter(1), reverse=True)
	stagingArea.sort(key=itemgetter(0))
	stagingArea=[card for pos, diff, name, card in stagingArea]
	counter = -1
	lastName = ''
	cardCount = 0
	for card in stagingArea:
		if card.Name != lastName or cardCount >= 4 or card._id in attachDict:
			counter += 1
			lastName = card.Name
			cardCount = 0
			if card._id in attachDict: lastName = ''
		card.moveToTable((cardPoolPos + (cardSAWidth * counter) + (cardOverlap * cardCount))  * sideMultiplier, tableside + (card.height() + 10 + cardOverlap * cardCount) * sideMultiplier)
		card.sendToFront()
		cardCount += 1
	
	#Attached cards, alignment
	for cid in attachDict.keys():
		card = Card(cid)
		for i, c in enumerate(attachDict.get(cid, [])):
			if card not in stagingArea:
				Card(c).moveToTable(card.position[0] - cardOverlap * i * sideMultiplier, card.position[1])
			else:
				Card(c).moveToTable(card.position[0] + cardOverlap * i * sideMultiplier, card.position[1])
			Card(c).sendToBack()

def _getCardPool():
	global tableside, sideMultiplier
	mute()
	cardPool=[((card.position[0] * sideMultiplier), card) for card in table 
              if card.controller == me 
              and (card.position[0] * sideMultiplier) >= (cardPoolPos - 25)
              and card.position[1] > (tableside - 25) 
              and card.position[1] < (tableside + 25)]
	cardPool.sort()
	cardPool=[card for pos, card in cardPool]
	return cardPool

def _alignCardPool(cardPool = []):
	mute()
	for counter, card in enumerate(cardPool):
		card.moveToTable((cardPoolPos + counter * cardPoolWidth)  * sideMultiplier,tableside)

def toggleProgDiff(card, x = 0, y = 0):
	mute()
	cardPool = _getCardPool()
	if card in cardPool:
		if card.highlight == NoDiffColor:
			card.highlight = None
			notify('{} returns {} to progressive difficulty.'.format(me, card))
		else:
			card.highlight = NoDiffColor
			notify('{} removes {} from progressive difficulty.'.format(me, card))


def commit(card, x = 0, y = 0):
	mute()
	card.orientation ^= Rot90
	if card.orientation & Rot90 == Rot90:
		notify('{} commits {}'.format(me, card))
	else:
		notify('{} readies {}'.format(me, card))

def doesNotReady(card, x = 0, y = 0):
	if card.highlight == DoesntUntapColor:
		card.highlight = None
		notify("{0}'s {1} can now ready during {0}'s Ready step.".format(me, card))
	else:
		card.highlight = DoesntUntapColor
		notify("{0}'s {1} will not ready during {0}'s Ready step.".format(me, card))

def flip(card, x = 0, y = 0):
	mute()
	card.isFaceUp = not card.isFaceUp

def block(card, x = 0, y = 0):
	global isBlock
	card.highlight = BlockColor
	notify('{} blocks with {}'.format(me, card))
	isBlock = 1
	play(card)

def activate(card, x = 0, y = 0):
	str = card.CardText
	strarray = re.split(r"\s+\s+",str)
#seriously, wtf is going on here?
#	i = 0
#	while i<(len(strarray)):
#		i+=1
	count = askInteger("Use which ability?", len(strarray))
	notify("{} activates the ability {}".format(me,strarray[count-1]))

def clear(card, x = 0, y = 0):
	notify("{} clears {}.".format(me, card))
	card.highlight = None
	card.target(False)

def addMarker(cards, x = 0, y = 0):
	mute()
	marker, quantity = askMarker()
	if quantity == 0: return
	for c in cards:
		c.markers[marker] += quantity
		notify("{} adds {} {} counters to {}.".format(me, quantity, marker[0], c))

def addPlusDamageMarker(card, x = 0, y = 0):
	mute()
	notify("{} adds a +1 damage counter to {}.".format(me, card))
	if MinusDamageMarker in card.markers:
		card.markers[MinusDamageMarker] -= 1
	else:
		card.markers[PlusDamageMarker] += 1
		
def addMinusDamageMarker(card, x=0, y=0):
	mute()
	notify("{} adds a -1 damage counter to {}.".format(me, card))
	if PlusDamageMarker in card.markers:
		card.markers[PlusDamageMarker] -= 1
	else:
		card.markers[MinusDamageMarker] += 1
		
def addPlusSpeedMarker(card, x = 0, y = 0):
	mute()
	notify("{} adds a +1 speed counter to {}.".format(me, card))
	if MinusSpeedMarker in card.markers:
		card.markers[MinusSpeedMarker] -= 1
	else:
		card.markers[PlusSpeedMarker] += 1
		
def addMinusSpeedMarker(card, x = 0, y = 0):
	mute()
	notify("{} adds a -1 speed counter to {}.".format(me, card))
	if PlusSpeedMarker in card.markers:
		card.markers[PlusSpeedMarker] -= 1
	else:
		card.markers[MinusSpeedMarker] += 1 

#---------------------------
#movement actions
#---------------------------

def setHost(group, x = 0, y = 0):
	global tableside, sideMultiplier
	host = me.hasInvertedTable()
	if host:
		notify("{} is not the host and has an inverted table.".format(me));
		tableside = (cardOverlap + me.Deck[0].height()) * -1
	else:
		notify("{} is the host and their table is not inverted.".format(me));
		tableside = cardOverlap
	sideMultiplier = tableside/abs(tableside)

def play(card):
	global isBlock
	global tableside, sideMultiplier
	if tableside is None:
		setHost(card.group)     
	mute()
	cardPool = _getCardPool()
	_realignCards()
	fromGroup = card.group.name
	card.moveToTable((cardPoolPos + len(cardPool) * cardPoolWidth)  * sideMultiplier,tableside)
	progDiff = len([pCard for pCard in cardPool if pCard.highlight != NoDiffColor])
	diff = progDiff + int(card.Difficulty)
	if(isBlock == 0):
		notify("{} plays {} from his {}. Base Difficulty: {}.".format(me, card, fromGroup, diff))
	else:
		isBlock = 0
	conf = confirm("Perform a Control Check?")
	if(conf):
		check()

def discard(card, x = 0, y = 0):
	mute()
	src = card.group
	fromText = " from the game area" if src == table else " from their " + src.name
	card.moveTo(me.Discard)
	notify("{} discards {}{}.".format(me, card, fromText))
	_realignCards()

def destroy(card, x = 0, y = 0):
	mute()
	src = card.group
	fromText = " from the game area" if src == table else " from their " + src.name
	card.moveTo(me.Discard)
	notify("{} destroys {}{}.".format(me, card, fromText))
	_realignCards()

def todeck(card, x = 0, y = 0):
	mute()
	src = card.group
	fromText = " from the game area" if src == table else " from their " + src.name
	card.moveTo(me.Deck)
	notify("{} returns {} to their deck{}.".format(me, card, fromText))
	_realignCards()

def tohand(card, x = 0, y = 0):
	mute()
	src = card.group
	fromText = " from the game area" if src == table else " from their " + src.name
	card.moveTo(me.hand)
	notify("{} returns {} to their hand{}.".format(me, card.name, fromText))
	_realignCards()

def rfg(card, x = 0, y = 0):
	mute()
	src = card.group
	fromText = " from the game area" if src == table else " from their " + src.name
	card.moveTo(me.piles['Removed From Game Zone'])
	notify("{} removes {} from the game {}.".format(me, card, fromText))
	_realignCards()

#---------------------------------------------------------------------------
# Hand actions
#---------------------------------------------------------------------------

def randomDiscard(group):
	mute()
	card = group.random()
	if card is None: return
	notify("{} randomly discards a card.".format(me))
	card.moveTo(me.Discard)

def mulligan(group):
	mute()
	newCount = len(group)
	if newCount < 0: return
	if not confirm("Use your once per game mulligan?"): return
	notify("{} uses their once per game mulligan.".format(me))
	for card in group:
		card.moveTo(me.piles['Removed From Game Zone'])
	me.Deck.shuffle()
	for card in me.Deck.top(newCount):
		card.moveTo(me.hand)

#---------------------------------------------------------------------------
# Piles actions
#---------------------------------------------------------------------------

def startDeck(group, x = 0, y = 0):
	global tableside, sideMultiplier
	global handSize
	global doAlignment
	mute()
	if not confirm("Are you sure?"): return
	myCards = (card for card in table
                    if card.controller == me
                    and card.owner == me)
	for card in myCards: 
		card.moveTo(me.Deck)
	for c in me.hand: c.moveTo(me.Deck)
	for c in me.Discard: c.moveTo(me.Deck)
	for c in me.piles['Removed From Game Zone']: c.moveTo(me.Deck)
	
	chars = {}
	for card in me.Deck:
		card.isFaceUp=True
		delayvar=rnd(10,1000)
		if re.search(r'character',card.Type,re.I):
			chars[card.Name]=[card,card.Vitality,card.properties['Hand Size']]
		card.isFaceUp=False
		delayvar=rnd(10,1000)
	charKeys=chars.keys()
	charIndex = 0
	if len(charKeys) == 0: return
	if len(charKeys) > 1:
		charIndex = askChoice('Which character are you starting with?',charKeys)
	if charIndex is None: return
	char=chars[charKeys[charIndex]][0]
	if tableside is None:
		setHost(group)     
	char.moveToTable((cardPoolPos-cardPoolWidth)  * sideMultiplier,tableside,True)
	me.Deck.shuffle()
	handSize=int(chars[charKeys[charIndex]][2])
	drawMany(me.Deck,handSize)
	me.life = int(chars[charKeys[charIndex]][1])
	doAlignment = True
	notify('{} is ready to play.'.format(me))

def draw(group, x = 0, y = 0):
	if len(group) == 0: 
		cycleDeck()
	mute()
	group[0].moveTo(me.hand)
	notify("{} draws a card.".format(me))

def drawMany(group, count = None):
	global handSize
	if len(group) == 0:
		cycleDeck()
	mute()
	drawDef=handSize
	if drawDef is not None and drawDef > 0:
		drawDef = drawDef - len(me.hand)
		if drawDef < 0: drawDef = 0
	else:
		drawDef = 7
	if count is None: count = askInteger("Draw how many cards?", drawDef)
	newcount = count
	for c in group.top(count):
		c.moveTo(me.hand)
		newcount -= 1
	if(newcount>0):
		cycleDeck()
		for c in group.top(newcount):
			c.moveTo(me.hand)
	notify("{} draws {} cards.".format(me, count))

def mill(group = me.Deck, count = None):
	if len(group) == 0:
		cycleDeck()
	mute()
	if count is None: count = askInteger("Mill how many cards?", 1)
	newcount = count
	for c in group.top(count):
		c.moveTo(me.Discard)
		newcount -= 1
	if(newcount>0):
		cycleDeck()
		for c in group.top(newcount):
			c.moveTo(me.Discard)
	notify("{} mills the top {} cards from his Deck.".format(me, count))

def rfgMany(group = me.Deck, count = None):
	if len(group) == 0:
		cycleDeck()
	mute()
	if count is None: count = askInteger("Remove how many cards?", 1)
	newcount = count
	for c in group.top(count):
		c.moveTo(me.piles['Removed From Game Zone'])
		newcount -= 1
	if(newcount>0):
		cycleDeck()
		for c in group.top(newcount):
			c.moveTo(me.piles['Removed From Game Zone'])
	notify("{} removes the top {} cards from his Deck.".format(me, count))

def shuffle(group = me.Deck, x = 0, y = 0):
	group.shuffle()

def shuffleIntoDeck(group = me.Discard):
	mute()
	for c in group: c.moveTo(me.Deck)
	me.Deck.shuffle()
	notify("{} shuffles his {} into his Deck.".format(me, group.name))

def moveIntoDeck(group):
	mute()
	for c in group: c.moveTo(me.Deck)
	notify("{} moves his {} into his Deck.".format(me, group.name))

def revealtopDeck(group, x = 0, y = 0):
	mute()
	if group[0].isFaceUp:
		notify("{} hides {} from the top of their Deck.".format(me, group[0]))
		group[0].isFaceUp = False
	else:
		group[0].isFaceUp = True
		notify("{} reveals {} from the top of their Deck.".format(me, group[0]))
		
def check(group = me.Deck):
	if len(group) == 0:
		cycleDeck()
	mute()
	card = group[0]
	card.isFaceUp = True
	delayvar = rnd(10,1000) #WONT WORK WITHOUT THIS LINE
	notify("{} checked a {} from his library.".format(me, card.Control))
	card.moveTo(me.Discard)


def cycleDeck(group = me.Deck):
	shuffleIntoDeck()
	if len(group) == 0: return
	count = 10
	for c in group.top(count): c.moveTo(me.piles['Removed From Game Zone'])
	notify("{} cycles their deck.".format(me))