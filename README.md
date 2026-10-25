# SaeVocalLab Webサイト

## ページ一覧
| ファイル | ページ |
|---|---|
| index.html | トップ |
| lesson/vocal.html | ボーカル（ポップス・ロック） |
| lesson/voice-training.html | ボイストレーニング基礎 |
| lesson/kids.html | キッズボーカル |
| lesson/adult.html | 大人・シニアボーカル |
| lesson/sing-play.html | 弾き語りボーカル |
| lesson/audition.html | オーディション・発表会対策 |

## SEO・AI検索対策（tools/seo_build.py）
各ページの構造化データ（JSON-LD）・正式URL・OGP、sitemap.xml / robots.txt / llms.txt は
`tools/seo_build.py` で自動生成しています。各HTMLの `<!-- SEO:START -->`〜`<!-- SEO:END -->` は直接編集しないでください。

実行：サイトのフォルダで `python3 tools/seo_build.py`（beautifulsoup4 が必要。`pip install beautifulsoup4`）
実行すると最後に「公開前チェック」の結果が表示されます。

**再実行が必要なとき**
- メールアドレス・LINEのURLを変えたとき → スクリプト冒頭の `SCHOOL['email']` / `SCHOOL['line']`（各HTMLのボタンのリンク先も変更）
- InstagramのURL・GoogleビジネスプロフィールのURLができたとき → `SCHOOL['sameAs']` に入力
- 定休日があるとき → `SCHOOL['openingHours']` の曜日から外す（現在は毎日10:00〜21:00）
- 料金が変わったとき → `SCHOOL['price']`
- ページのタイトル・説明文・見出し・リード文を変えたとき

**仮原稿は構造化データに入れない仕組み**
- `SCHOOL` で None の項目（メール）は出力されません。電話番号は掲載しない方針のため、項目自体を設けていません。
- 「よくあるご質問」は `FAQ_CONFIRMED` に入れたページだけ出力します。トップのFAQ（サイト掲載の事実のみで作成）は出力済み。
  レッスンページのFAQは、回答を確認したらページを追加して再実行してください。
- 「生徒さんの声」は構造化データに出力しません（自社サイトの口コミはGoogleのレビュー表示の対象外で、架空の声を載せるとガイドライン違反になるため）。

**AIの巡回設定**：robots.txt の許可・拒否は `AI_CRAWLERS` で切り替えられます（現在はすべて許可）。

## 方針
- 電話番号はサイト・構造化データ・llms.txt のいずれにも掲載しません（お申し込みはメール・LINEのみ）。
- SNSは Instagram のみ。

## 追加した画像
| ファイル | 用途 |
|---|---|
| assets/img/ogp.jpg | トップページのSNSシェア画像（1200×630、トップ写真から切り出し） |
| assets/img/logo.png | 構造化データ用のロゴ（512×512） |
| assets/img/line-qr.png | LINE友だち追加のQRコード（PCのお申し込み欄に表示。スマホでは非表示でLINEボタンから追加） |
| assets/img/apple-touch-icon.png | スマホのホーム画面アイコン（180×180） |

レッスンページのシェア画像は、各ページの写真（lesson-*.jpg）を使います。

## 公開前に
- Instagram・Privacy Policy のリンク先（現在は `#`）を差し替え、`tools/seo_build.py` を再実行
  - Instagram のボタンは各ページのフッターとスマホメニューにあります（`class="sns__ig"` の href）
- `tools/` フォルダと README.md はサーバーにアップロード不要
- Google アナリティクス等の計測タグを各ページの `<head>` に追加
- Google Search Console と Bing Webmaster Tools に登録し、sitemap.xml（https://saevocallab.jp/sitemap.xml）を送信
- Googleビジネスプロフィールを「SaeVocalLab」で登録し、URLを `SCHOOL['sameAs']` に入れて再実行
