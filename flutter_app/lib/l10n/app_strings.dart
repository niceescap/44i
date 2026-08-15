import 'dart:ui' as ui;

const supportedOracleLocales = <String>{
  'fr', 'en', 'es', 'it', 'de', 'nl', 'pt', 'pl', 'hu', 'sr',
  'ru', 'ar', 'he', 'zh', 'th', 'ja', 'ko', 'hi', 'id', 'tr', 'vi',
};

String deviceLocale() {
  final code = ui.PlatformDispatcher.instance.locale.languageCode.toLowerCase();
  return supportedOracleLocales.contains(code) ? code : 'fr';
}

class AppStrings {
  const AppStrings(this.locale);
  final String locale;

  bool get en => locale == 'en';

  String get title => 'La Rosace';
  String get tagline => en ? 'Anonymous symbolic reading' : 'Consultation Symbolique anonyme';
  String get subtitle => en ? 'The Oracle guides you' : 'l’Oracle vous guide';
  String get writeHint => en ? 'Write to the oracle…' : 'Écris à l’oracle…';
  String get keep => en ? 'Keep this reading' : 'Conserver ce tirage';
  String get again => en ? 'Start over' : 'Recommencer';
  String get donate => en ? 'Donate to La Rosace' : 'Faire un don à La Rosace';
  String get premium => en ? 'Try the Premium version' : 'Tester la version Premium';
  String get premiumTitle => 'La Grande Rosace';
  String get premiumBody => en
      ? 'Thank you for your interest. A fuller version is in development: the most capable French-language model specialised in cartomancy. The three-card reading is a free excerpt. Leave your e-mail to be notified.'
      : 'Merci de l’attention que vous portez à La Rosace ! Une version complète est en cours de développement. Vous pourrez alors exploiter toute la puissance d’interprétation de notre intelligence artificielle, instruite sur plusieurs milliards de paramètres. Il s’agit du plus gros modèle francophone spécialisé en cartomancie, dont le tirage de trois cartes est un simple extrait offert. Laissez votre e-mail pour être prévenu(e).';
  String get notifyMe => en ? 'Notify me' : 'Prévenez-moi';
  String get emailHint => 'votre.email@exemple.fr';
  String get thanks => en
      ? 'Thank you. We will let you know.'
      : 'Merci. Votre adresse est notée, nous vous préviendrons.';
  String get silent => en ? 'The oracle is silent for a moment.' : 'L’oracle est silencieux un instant.';
  String get tableFail => en
      ? 'The cloth could not be prepared. Try again.'
      : 'Le tapis n’a pas pu se préparer. Réessaie.';
  String get privacy => en ? 'Privacy' : 'Confidentialité';
  String get legal => 'La Rosace, par « 44 interprètes » ★ V3 · 15 août 2026';
  String get audioPremium => en ? 'premium feature' : 'fonction premium';
  String get listen => en ? 'Listen' : 'Écouter';
  String get close => en ? 'Close' : 'Fermer';
  String get none => en ? '(no exchange)' : '(aucun échange)';
  String get user => en ? 'user' : 'utilisateur';
  String get oracle => 'oracle';

  static const ask = [
    'Choisis trois cartes.',
    'Clique trois fois là où ça t’inspire.',
    'Sélectionne avec soin trois cartes.',
    'Quelles sont les trois cartes qui t’attirent ?',
    'Relève trois cartes cachées.',
    'Laisse ta main choisir trois voiles.',
    'Trois cartes suffisent. Pose le premier geste.',
    'Approche-toi du tapis et désigne trois destins.',
  ];
  static const askEn = [
    'Choose three cards.',
    'Tap three times where you feel drawn.',
    'Select three cards with care.',
    'Which three cards attract you?',
    'Lift three hidden cards.',
    'Let your hand choose three veils.',
    'Three cards are enough. Make the first gesture.',
    'Approach the cloth and name three destinies.',
  ];
  static const more = [
    'Une autre…',
    'Encore une.',
    'Poursuis, une deuxième carte.',
    'Le tapis attend le deuxième geste.',
    'Laisse venir la suivante.',
    'Une de plus, sans te presser.',
  ];
  static const moreEn = [
    'Another…',
    'One more.',
    'Continue, a second card.',
    'The cloth waits for the second gesture.',
    'Let the next one come.',
    'One more, without hurry.',
  ];
  static const last = [
    'Plus qu’une…',
    'Et la dernière…',
    'Et la troisième pour finir.',
    'Il reste le dernier voile.',
    'Une dernière fois, là où ça t’appelle.',
    'Ferme le triangle.',
  ];
  static const lastEn = [
    'One left…',
    'And the last…',
    'And the third to finish.',
    'The last veil remains.',
    'One last time, where it calls you.',
    'Close the triangle.',
  ];
  static const wait = [
    'Le tirage est bien enregistré. L’oracle en prend connaissance.',
    'Les trois cartes sont posées. Le cabinet s’ouvre.',
    'C’est noté. L’interprétation se prépare.',
    'Le tapis se tait. L’oracle lit.',
    'La main est complète. Un instant de silence…',
    'Tout est reçu. L’oracle assemble le sens.',
  ];
  static const waitEn = [
    'The draw is recorded. The oracle is reading it.',
    'The three cards are down. The cabinet opens.',
    'Noted. The interpretation is being prepared.',
    'The cloth falls silent. The oracle reads.',
    'The hand is complete. A moment of silence…',
    'All is received. The oracle gathers the meaning.',
  ];
  static const disclaimer = [
    'Garde en tête que La Rosace est une application de divertissement : ces mots stimulent la pensée, ils ne dictent pas ta vie.',
    'Rappel doux : ici tout est symbolique et ludique, jamais un avis médical, juridique ou financier.',
    'Reçois ce qui vient comme une conversation philosophique, non comme une vérité absolue.',
    'La Rosace divertit. Les cartes ouvrent des pistes, elles ne remplacent aucun professionnel.',
    'Ceci n’est pas une prédiction certaine, seulement un jeu d’images pour réfléchir.',
    'L’intelligence artificielle assemble ici des savoirs de tradition : prends-les à titre de stimulation, pas d’autorité.',
    'Amuse-toi du miroir. Ce n’est ni diagnostic, ni contrat, ni oracle infaillible.',
    'Le cabinet est un théâtre symbolique. Ce qui compte, c’est ce que tu y reconnais.',
    'Les interprétations viennent d’ouvrages ésotériques et d’un modèle : lis-les comme on lit un poème utile.',
    'Pas de fatalité. Juste trois cartes, un récit, et ta liberté d’en faire ce que tu veux.',
    'Si un sujet grave se présente, tourne-toi vers une personne compétente. Ici, on joue avec les symboles.',
    'La Rosace t’accompagne le temps d’une lecture légère. Le sérieux de ta vie reste le tien.',
  ];
  static const disclaimerEn = [
    'Keep in mind that La Rosace is entertainment: these words stimulate thought, they do not dictate your life.',
    'A gentle reminder: everything here is symbolic and playful, never medical, legal or financial advice.',
    'Receive what comes as a philosophical conversation, not as absolute truth.',
    'La Rosace entertains. The cards open paths; they replace no professional.',
    'This is not a certain prediction, only a play of images for reflection.',
    'The model assembles traditional knowledge: take it as stimulation, not authority.',
    'Enjoy the mirror. It is neither diagnosis, nor contract, nor infallible oracle.',
    'The cabinet is a symbolic theatre. What matters is what you recognise.',
    'Readings come from esoteric works and a model: read them as a useful poem.',
    'No fatality. Just three cards, a story, and your freedom.',
    'If a serious matter arises, turn to a competent person. Here we play with symbols.',
    'La Rosace stays for a light reading. The seriousness of your life remains yours.',
  ];

  List<String> get askLines => en ? askEn : ask;
  List<String> get moreLines => en ? moreEn : more;
  List<String> get lastLines => en ? lastEn : last;
  List<String> get waitLines => en ? waitEn : wait;
  List<String> get discLines => en ? disclaimerEn : disclaimer;
}
