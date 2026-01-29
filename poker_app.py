import streamlit as st
import random
from treys import Card, Evaluator, Deck

# --- UTILITY: CLEAN INPUTS ---
def clean_card_input(card_str):
    """
    Robust cleaner:
    - Handles lowercase ('ah' -> 'Ah')
    - Handles '10' ('10s' -> 'Ts')
    - Removes spaces
    """
    if not card_str: return ""
    clean = card_str.strip().replace(" ", "").replace("10", "T")
    if len(clean) >= 2:
        # Capitalize Rank, lowercase Suit (e.g., 'As')
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
    if not board_strs or len(board_strs) < 3:
        return "N/A", False
    
    try:
        cards = [Card.new(clean_card_input(c)) for c in board_strs]
        suits = [Card.get_suit_int(c) for c in cards]
        max_suit_count = max([suits.count(s) for s in set(suits)])
        
        ranks = sorted([Card.get_rank_int(c) for c in cards])
        is_connected = any(ranks[i+1] - ranks[i] <= 2 for i in range(len(ranks)-1))
        
        is_wet = max_suit_count >= 2 or is_connected
        return ("Wet" if is_wet else "Dry"), is_wet
    except:
        return "N/A", False

def calculate_equity(hero_hand, board_strs, street, sims=2500):
    evaluator = Evaluator()
    wins, ties = 0, 0
    
    # Validation
    try:
        c1 = clean_card_input(hero_hand[0])
        c2 = clean_card_input(hero_hand[1])
        if not c1 or not c2: return 0, "Waiting for cards..."
        
        hero_cards = [Card.new(c1), Card.new(c2)]
        board_cards = []
        if board_strs:
            board_cards = [Card.new(clean_card_input(c)) for c in board_strs if c]
    except Exception:
        return 0, "Invalid Cards"

    current_strength = "N/A"
    if len(hero_cards + board_cards) >= 5:
        current_strength = get_hand_label(evaluator.evaluate(hero_cards, board_cards[:5]))

    for _ in range(sims):
        deck = Deck()
        # Remove known cards
        for c in (hero_cards + board_cards):
            if c in deck.cards: deck.cards.remove(c)
        
        opp_hand = deck.draw(2)
        cards_to_draw = 5 - len(board_cards)
        
        if cards_to_draw > 0:
            full_board = board_cards + deck.draw(cards_to_draw)
        else:
            full_board = board_cards
        
        h_score = evaluator.evaluate(hero_cards, full_board)
        opp_score = evaluator.evaluate(opp_hand, full_board)

        if h_score < opp_score: wins += 1
        elif h_score == opp_score: ties += 1
            
    return (wins + (ties * 0.5)) / sims * 100, current_strength

# --- UI LAYOUT ---
st.set_page_config(page_title="Pro Poker Engine", layout="wide")
st.title("🃏 Pro Poker Engine (bb)")

col1, col2 = st.columns([1, 1])

with col1:
    st.subheader("1. Hand Input")
    street = st.selectbox("Street", ["Pre-flop", "Flop", "Turn", "River"])
    
    c1, c2 = st.columns(2)
    # Empty default values so user can type fresh
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
    
    pos = st.radio("My Position", ["In Position (Last)", "Out of Position (First)"])

# --- EXECUTION ---
if st.button("Calculate Best Move"):
    # Input Validation
    if not h1 or not h2:
        st.error("Please enter your hole cards first.")
        st.stop()
        
    with st.spinner("Simulating Outcomes..."):
        equity, hand_type = calculate_equity([h1, h2], board_list, street)
    
    st.divider()

    # --- ADVANCED MATH ---
    # 1. Pot Odds: Cost / (Total Pot + Cost)
    pot_odds = 0.0
    if call_amount > 0:
        pot_odds = (call_amount / (pot_bb + call_amount)) * 100
        
    # 2. Expected Value (EV) of a Call
    # EV = (%Win * TotalPot) - (%Lose * CallAmount)
    total_pot_after_call = pot_bb + call_amount
    ev_value = ((equity / 100) * total_pot_after_call) - ((1 - (equity/100)) * call_amount)
    
    # 3. Required Fold Equity (Alpha) for Bluffs
    # If we bet 50% pot, opponent must fold 33% of time to breakeven
    # We display this only if suggesting a bet
    
    # --- METRICS ROW ---
    st.subheader("📊 Math Breakdown")
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Hand Equity", f"{equity:.1f}%", help="Chance you win by showdown")
    m2.metric("Pot Odds", f"{pot_odds:.1f}%", help="Equity needed to break even on a call")
    m3.metric("Exp. Value (EV)", f"{ev_value:+.1f} bb", help="Expected profit/loss in Big Blinds")
    
    # Placeholder for Fold Equity metric
    fold_metric_label = "Req. Fold %"
    fold_metric_val = "N/A"
    
    # --- DECISION LOGIC ---
    st.subheader("💡 Strategy Recommendation")
    
    if action == "Facing a Bet":
        # DEFENSE
        diff = equity - pot_odds
        if diff > 10:
            st.success("## ✅ RAISE (Value)")
            reasoning = f"You are crushing the pot odds. Your hand wins {equity:.1f}% of the time, but you only need {pot_odds:.1f}%. Raise for value."
        elif diff > 0:
            st.warning("## ✅ CALL")
            reasoning = f"Profitable call. You make {ev_value:.1f}bb on average every time you make this call."
        else:
            st.error("## ❌ FOLD")
            reasoning = f"Negative EV. You will lose {abs(ev_value):.1f}bb on average if you call. Wait for a better spot."
            
    else:
        # OFFENSE (Leads)
        texture_label, is_wet = analyze_texture(board_list)
        
        # Calculate optimal bet sizes
        bet_small = pot_bb * 0.33
        bet_large = pot_bb * 0.75
        
        # Calculate Fold Equity needed for those bets (Alpha)
        alpha_small = (0.33 / (1 + 0.33)) * 100 # ~25%
        alpha_large = (0.75 / (1 + 0.75)) * 100 # ~42%

        if street == "Pre-flop":
            if equity > 58:
                st.success("## 🟢 OPEN RAISE")
                reasoning = "Premium hand strength relative to random cards. Build the pot early."
            else:
                st.error("## ⚪ FOLD / LIMP")
                reasoning = "Hand is too weak to open the action from this position."
                
        else:
            # Post-flop Logic
            if equity > 65:
                # Value Bet Logic
                if is_wet:
                    st.success(f"## 🟢 BET: {bet_large:.1f}bb (75% Pot)")
                    fold_metric_val = f"{alpha_large:.0f}%"
                    reasoning = f"The board is Wet ({texture_label}). You have a strong hand but need to charge opponents to see the next card."
                else:
                    st.success(f"## 🟢 BET: {bet_small:.1f}bb (33% Pot)")
                    fold_metric_val = f"{alpha_small:.0f}%"
                    reasoning = f"The board is Dry ({texture_label}). Bet small to keep weaker hands in the pot (Value Extraction)."
                    
            elif equity > 45:
                st.info("## 🟡 CHECK")
                reasoning = "You have 'Showdown Value'. Your hand is good enough to win, but not strong enough to get called by worse hands if you bet."
                
            elif texture_label == "Wet" and 25 < equity < 45:
                # Semi-Bluff Logic
                st.warning(f"## 🔵 SEMI-BLUFF: {bet_large:.1f}bb (75% Pot)")
                fold_metric_val = f"{alpha_large:.0f}%"
                reasoning = f"You have low current strength but high potential (Draws). A large bet puts maximum pressure on them."
            else:
                st.error("## ⚪ CHECK / FOLD")
                reasoning = "Low equity and no significant draw potential. Do not put more money in."

    # Render Fold Equity if applicable
    m4.metric("Req. Fold %", fold_metric_val, help="How often opponent must fold for a bluff to break even")
    
    st.caption(f"Reasoning: {reasoning}")
