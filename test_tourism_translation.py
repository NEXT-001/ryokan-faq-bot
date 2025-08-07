#!/usr/bin/env python3
"""
Test script to specifically test tourism response translation behavior
"""
from services.unified_chat_service import UnifiedChatService

def test_tourism_translation():
    """Test tourism-specific response generation to identify translation inconsistencies"""
    
    chat_service = UnifiedChatService()
    
    print("="*80)
    print("TESTING TOURISM TRANSLATION BEHAVIOR")
    print("="*80)
    
    # Test cases that should trigger pure tourism responses
    test_cases = [
        {
            'input': '추천 관광지는?',
            'location': '鎌倉',
            'description': 'Korean query for tourist spots in Kamakura'
        },
        {
            'input': '추천 관광지는?',
            'location': '京都', 
            'description': 'Korean query for tourist spots in Kyoto'
        },
        {
            'input': '관광 명소 추천해주세요',
            'location': '福岡',
            'description': 'Korean request for tourist attractions in Fukuoka'
        }
    ]
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n{'-'*60}")
        print(f"TEST {i}: {test_case['description']}")
        print(f"Input: {test_case['input']}")
        print(f"Location: {test_case['location']}")
        print(f"{'-'*60}")
        
        try:
            # Force tourism intent by testing the tourism handler directly
            location_context = {'manual_location': test_case['location']}
            
            response = chat_service.get_unified_response(
                user_input=test_case['input'],
                company_id='demo-company',
                user_info="Test User",
                location_context=location_context
            )
            
            print(f"Response Type: {response.get('response_type', 'unknown')}")
            print(f"Original Language: {response.get('original_language', 'unknown')}")
            print(f"Confidence Score: {response.get('confidence_score', 'unknown')}")
            print("\nResponse Answer:")
            answer = response.get('answer', 'No answer')
            print(answer)
            
            # Detailed analysis of translation consistency
            print(f"\n📊 DETAILED ANALYSIS:")
            
            # Check for mixed language patterns
            korean_patterns = ['관광정보', '자세한', '정보', '영업중', '평가', '클릭', '확인']
            japanese_patterns = ['観光情報', '詳細', '営業中', '評価', 'クリック', '確認', 'を', 'に', 'は', 'が', 'です', 'ます']
            
            korean_count = sum(1 for pattern in korean_patterns if pattern in answer)
            japanese_count = sum(1 for pattern in japanese_patterns if pattern in answer)
            
            print(f"  Korean patterns found: {korean_count}")
            print(f"  Japanese patterns found: {japanese_count}")
            print(f"  Mixed language detected: {korean_count > 0 and japanese_count > 0}")
            
            # Check if this was supposed to be translated
            should_be_translated = response.get('original_language') != 'ja'
            was_translation_skipped = response.get('response_type') in ['tourism', 'restaurant']
            
            print(f"  Should be translated: {should_be_translated}")
            print(f"  Translation was skipped: {was_translation_skipped}")
            print(f"  Potential issue: {should_be_translated and was_translation_skipped and japanese_count > 0}")
            
        except Exception as e:
            print(f"Error: {e}")
            import traceback
            traceback.print_exc()
    
    print("\n" + "="*80)
    print("SPECIFIC ISSUE ANALYSIS:")
    print("="*80)
    print("The root cause of inconsistent translation behavior is in unified_chat_service.py:")
    print()
    print("LINE 155: if original_language != 'ja' and response.get('response_type') not in ['tourism', 'restaurant']:")
    print("         ❌ This excludes ALL 'tourism' responses from translation")
    print()
    print("However, there are multiple sources of tourism content:")
    print("1. format_google_places_response() - ✅ Already generates content in target language")
    print("2. generate_tourism_response_by_city() - ❌ May generate Japanese content even for foreign queries")
    print("3. Fallback tourism responses - ❌ Mixed language headers + untranslated content")
    print()
    print("SOLUTION: Check if tourism response contains mixed/untranslated content before skipping translation")

if __name__ == "__main__":
    test_tourism_translation()