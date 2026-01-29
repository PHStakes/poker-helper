import streamlit as st
import pandas as pd
from treys import Card, Evaluator, Deck

# --- UPDATED POSITION LOOKUP ---
POS_LOOKUP = {
    'ug': 'UTG', 'ep': 'EP', 'mp': 'MP', 'lj': 'LJ', 
    'hj': 'HJ', 'co': 'CO', 'bn': 'BTN', 'sb': 'SB', 'bb': 'BB'
}

# --- PARSING ENGINES ---
def parse_action_string(s):
    try:
        if not s or len(s) < 4: return None
        num_started = int(s[0])
        hero_pos_code = s[1:3].lower()
        actions = list(s[3:])
        
        # Determine active opponents (non-folds, excluding hero)
        # We assume actions follow seat order starting from UTG
        active_indices = [i for i, a in enumerate(actions) if a != 'f']
        num_opponents = len(active_indices) - 1 if len(active_indices) > 0 else 0
        
        # Determine Pot Type
        act_str = "".join(actions)
        if '4' in act_str: pot_type = "4-Bet Pot"
        elif '3' in act_str: pot_type = "3-Bet Pot"
        else: pot_type = "Raised Pot"
        
        pos_name = POS_LOOKUP.get(hero_pos_code, hero_pos_code.upper())
        return num_started, pos_name, num_opponents, pot_type
    except Exception:
        return None

def parse_cards(raw_input):
    # Standardize '10' to 't' then force 'T' for Treys compatibility
    clean = raw_input.strip().lower().replace("10", "t").replace(" ", "")
    cards = [clean[i:i+2] for i in range(0, len(clean), 2)]
    
    formatted = []
    for c in cards:
        if len(c) == 2:
            rank = c[0].upper() # Fixes KeyError: 't' -> 'T'
            suit = c[1].lower()
            formatted.append(f"{rank}{suit}")
            
    hero = formatted[:2]
    board = formatted[2:]
    
    count = len(board)
    if count == 0: street = "Pre-flop"
    elif count == 3: street = "Flop"
    elif count == 4: street = "Turn"
    elif count == 5: street = "River"
    else: street = "Partial"
    
    return hero, board, street

# --- SIMULATION ENGINE ---
def calculate_equity(hero_str, board_str, num_opps, sims=1000):
    evaluator = Evaluator()
    wins, ties = 0, 0
    try:
        hero_cards = [Card.new(c) for c in hero_str]
        board_cards = [Card.new(c) for c in board_str]
    except Exception:
        return 0, "Error"

    for _ in range(sims):
        deck = Deck()
        # Remove known cards from deck
        for c in (hero_cards + board_cards):
            if c in deck.cards: deck.cards.remove(c)
        
        opp_hands = [deck.draw(2) for _ in range(num_opps)]
        needed = 5 - len(board_cards)
        full_board = board_cards + (deck.draw(needed) if needed > 0 else [])
        
        # Score current hand vs best opponent hand
        h_score = evaluator.evaluate(hero_cards, full_board)
        o_scores = [evaluator.evaluate(opp, full_board) for opp in opp_hands]
        best_o = min(o_scores) if o_scores else 9999
        
        if h_score < best_o: wins += 1
        elif h_score == best_o: ties += 1
            
    label = "N/A"
    if len(hero_cards + board_cards) >= 5:
        label = evaluator.class_to_string(evaluator.get_rank_class(evaluator.evaluate(hero_cards, board_cards[:5])))
    return (wins + (ties * (1/(num_opps+1)))) / sims * 100, label

# --- UI ---
st.set_page_config(page_title="Stakked Poker", layout="wide")
st.title("🃏 Stakked Poker")

# --- TWO-LINE INPUT SECTION ---
st.subheader("⚡ Quick Entry")
c1, c2 = st.columns(2)

with c1:
    act_string = st.text_input("ACTION (e.g., 6bnffrfff)", placeholder="[Size][Pos][Actions]").lower()
    parsed_act = parse_action_string(act_string)

with c2:
    card_string = st.text_input("CARDS (e.g., asks7h8c2d)", placeholder="Hole+Board").lower()
    hero_p, board_p, street = parse_cards(card_string)

if parsed_act and hero_p:
    n_start, h_pos, n_opps, p_type = parsed_act
    st.info(f"📍 **{street}** | {h_pos} in {p_type} vs {n_opps} Opponents")

# --- POT CONTEXT ---
p1, p2, p3 = st.columns(3)
pot_bb = p1.number_input("Pot Size (bb)", 1.0, 2000.0, 15.0)
facing_bet = p2.radio("Status", ["Checked to Me", "Facing a Bet"])
call_bb = p3.number_input("To Call (bb)", 0.0, 1000.0, 5.0) if facing_bet == "Facing a Bet" else 0.0

# --- ANALYSIS ---
if st.button("🔥 RUN GTO ANALYSIS"):
    if not act_string or not card_string:
        st.error("Missing input data.")
    else:
        with st.spinner("Calculating..."):
            equity, hand_type = calculate_equity(hero_p, board_p, n_opps)
        
        st.divider()
        
        # MATH RESULTS
        odds = (call_bb / (pot_bb + call_bb)) * 100 if call_bb > 0 else 0
        ev = ((equity / 100) * (pot_bb + call_bb)) - ((1 - (equity/100)) * call_bb)
        
        res1, res2, res3 = st.columns(3)
        res1.metric("Win Prob", f"{equity:.1f}%")
        res2.metric("Hand Type", hand_type)
        res3.metric("EV", f"{ev:+.2f} bb")

        # STRATEGY
        st.subheader("💡 Recommendation")
        if facing_bet == "Facing a Bet":
            diff = equity - odds
            if diff > 10: st.success("## ✅ RAISE"); msg = "Significant equity edge."
            elif diff > 0: st.warning("## ✅ CALL"); msg = "Pot odds justify continuing."
            else: st.error("## ❌ FOLD"); msg = f"Equity ({equity:.1f}%) is too low for this price ({odds:.1f}%)."
        else:
            if equity > 60: st.success("## 🟢 VALUE BET"); msg = "Charge weaker ranges."
            elif equity > 40: st.info("## 🟡 CHECK"); msg = "Protect showdown value."
            else: st.error("## ⚪ CHECK / FOLD"); msg = "Weak equity; don't bloat the pot."
        
        st.write(f"**Analysis:** {msg}")

with st.expander("📊 Range Reference"):
    st.write("Current Position Codes:")
    st.write(", ".join([f"**{k}**: {v}" for k, v in POS_LOOKUP.items()]))
