import streamlit as st
import random
from treys import Card, Evaluator, Deck

# --- UTILITY: CLEAN INPUTS ---
def clean_card_input(card_str):
    if not card_str: return ""
    clean = card_str.strip().replace(" ", "").replace("10", "T")
    if len(clean) >= 2:
        return clean[0].upper() + clean[1].lower()
    return clean

# --- ANALYTICS ENGINE ---
def get_hand_label(score):
    if score <= 10: return "Royal Flush"
    if score <= 166: return "Straight Flush"
    if score <= 322: return "Four of a Kind"
    if score <= 1599: return "Full House"
    if score <= 1609: return "Flush"
    if score <= 1620: return "Straight"
    if score <= 2467: return "Three of a Kind"
    if score <= 3325: return "Two Pair"
    if score <= 6185: return "Pair"
    return "High Card"

def analyze_texture(board_strs):
    if not board_strs or len(board_strs) < 3: return "N/A", False
    try:
        cards = [Card.new(clean_card_input(c)) for c in board_strs]
        suits = [Card.get_suit_int(c) for c in cards]
        max_suit = max([suits.count(s) for s in set(suits)])
        ranks = sorted([Card.get_rank_int(c) for c in cards])
        is_connected = any(ranks[i+1] - ranks[i] <= 2 for i in range(len(ranks)-1))
        is_wet = max_suit >= 2 or is_connected
        return ("Wet" if is_wet else "Dry"), is_wet
    except: return "N/A", False

def calculate_equity(hero_hand, board_strs, num_players, sims=2000):
    evaluator = Evaluator()
    wins, ties = 0, 0
    
    try:
        c1, c2 = clean_card_input(hero_hand[0]), clean_card_input(hero_hand[1])
        if not c1 or not c2: return 0, "Waiting..."
        hero_cards = [Card.new(c1), Card.new(c2)]
        board_cards = [Card.new(clean_card_input(c)) for c in board_strs if c] if board_strs else []
    except: return 0, "Invalid Cards"

    current_strength = "N/A"
    if len(hero_cards + board_cards) >= 5:
        current_strength = get_hand_label(evaluator.evaluate(hero_cards, board_cards[:5]))

    for _ in range(sims):
        deck = Deck()
        known = hero_cards + board_cards
        for c in known: 
            if c in deck.cards: deck.cards.remove(c)
            
        # Draw for ALL opponents (multi-way logic)
        opp_hands = []
        for _ in range(num_players - 1):
            opp_hands.append(deck.draw(2))
            
        cards_needed = 5 - len(board_cards)
        full_board = board_cards + (deck.draw(cards_needed) if cards_needed > 0 else [])
        
        hero_score = evaluator.evaluate(hero_cards, full_board)
        
        # Find the BEST opponent score (lowest is best)
        best_opp_score = min([evaluator.evaluate(h, full_board) for h in opp_hands])

        if hero_score < best_opp_score: wins += 1
        elif hero_score == best_opp_score: ties += 1  # Split pot
            
    return (wins + (ties * (1/num_players))) / sims * 100, current_strength

# --- UI LAYOUT ---
st.set_page_config(page_title="Multiway Poker Engine", layout="wide")
st.title("🃏 Pro Poker Engine (Multi-way)")

col1, col2 = st.columns([1, 1])

with col1:
    st.subheader("1. Hand & Players")
    c_street, c_players = st.columns(2)
    street = c_street.selectbox("Street", ["Pre-flop", "Flop", "Turn", "River"])
    num_players = c_players.number_input("Players in Hand", min_value=2, max_value=9, value=2)
    
    c1, c2 = st.columns(2)
    h1 = c1.text_input("Hole Card 1", "")
    h2 = c2.text_input("Hole Card 2", "")
    
    board_list = []
    if street != "Pre-flop":
        board_input = st.text_input("Board (e.g. Th 7d 2s)", "")
        board_list = board_input.split()

with col2:
    st.subheader("2. Action & Pot")
    pot_bb = st.number_input("Current Pot (bb)", min_value=1.0, value=10.0)
    action = st.radio("Situation", ["Checked to Me / I Act First", "Facing a Bet"])
    
    call_amount = 0.0
    if action == "Facing a Bet":
        call_amount = st.number_input("Amount to Call (bb)", min_value=0.1, value=5.0)
    
    pos = st.radio("My Position", ["In Position", "Out of Position"])

# --- EXECUTION ---
if st.button("Calculate Best Move"):
    if not h1 or not h2:
        st.error("Enter cards first.")
        st.stop()
        
    with st.spinner(f"Simulating against {num_players - 1} opponents..."):
        equity, hand_type = calculate_equity([h1, h2], board_list, num_players)
    
    st.divider()

    # --- MATH & METRICS ---
    pot_odds = (call_amount / (pot_bb + call_amount)) * 100 if call_amount > 0 else 0
    total_pot = pot_bb + call_amount
    ev_value = ((equity / 100) * total_pot) - ((1 - (equity/100)) * call_amount)
    
    # Fair Share: The "Average" equity you should expect (e.g. 50% for 2 players, 33% for 3)
    fair_share = 100 / num_players
    
    st.subheader("📊 Multi-way Analytics")
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Hand Equity", f"{equity:.1f}%", delta=f"{equity-fair_share:.1f}% vs Fair Share")
    m2.metric("Pot Odds", f"{pot_odds:.1f}%")
    m3.metric("Exp. Value (EV)", f"{ev_value:+.1f} bb")
    m4.metric("Players", f"{num_players}")
    
    # --- STRATEGY ENGINE ---
    st.subheader("💡 Strategic Advice")
    texture_label, is_wet = analyze_texture(board_list)
    reasoning = ""
    
    if action == "Facing a Bet":
        diff = equity - pot_odds
        if diff > 5: # Tighter threshold for multiway
            st.success("## ✅ CALL / RAISE")
            reasoning = f"You are getting {pot_odds:.1f}% odds but have {equity:.1f}% equity. Even with {num_players} players, this is profitable."
        elif diff > -2: # Slight buffer
            st.warning("## 🟡 MARGINAL CALL")
            reasoning = "Close decision. In multi-way pots, players usually have stronger hands. Proceed with caution."
        else:
            st.error("## ❌ FOLD")
            reasoning = f"Multi-way trap. You need {pot_odds:.1f}% equity but only have {equity:.1f}%. Your EV is {ev_value:.1f}bb."
            
    else: # Hero is Leading
        # In multi-way pots, we size down bluffs and value bet strictly
        if equity > (fair_share * 1.5): # e.g. >50% in 3-way
            size = 0.6 if is_wet else 0.4
            st.success(f"## 🟢 VALUE BET ({pot_bb * size:.1f}bb)")
            reasoning = f"You are well ahead of the {fair_share:.0f}% fair share. Bet for value, but respect that 3+ players makes it harder to hold."
        elif equity > fair_share and is_wet:
            st.warning("## 🔵 SEMI-BLUFF / CHECK")
            reasoning = "Multi-way bluffs are risky. Only bet if you have the Nut Flush/Straight draw."
        else:
            st.error("## ⚪ CHECK / FOLD")
            reasoning = "In multi-way pots, don't bluff without huge equity. Check and try to realize your equity for free."

    st.caption(f"Reasoning: {reasoning}")
