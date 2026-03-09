<script setup>
</script>

<template>
  <div class="min-h-screen bg-gray-50 dark:bg-gray-900">
    <div class="container mx-auto px-4 py-6 max-w-3xl">
      <h1 class="text-2xl md:text-3xl font-bold text-gray-800 dark:text-white mb-6">
        <i class="fas fa-shield-alt text-primary-600 mr-2"></i>
        Politique de retrait de contenu
      </h1>

      <div class="space-y-6 text-gray-700 dark:text-gray-300 text-sm leading-relaxed">
        <!-- Disclaimer -->
        <section class="card p-6">
          <h2 class="text-lg font-semibold text-gray-800 dark:text-white mb-3">
            <i class="fas fa-info-circle text-primary-600 mr-2"></i>
            Avertissement
          </h2>
          <p>
            Ce site est un outil communautaire permettant le partage et la gestion de visuels
            et d'archives audio au format MYO Studio. Les contenus sont partagés par les
            utilisateurs de la communauté et ne sont pas produits par ce site.
          </p>
          <p class="mt-2">
            Nous ne revendiquons aucun droit de propriété intellectuelle sur les contenus
            partagés par les utilisateurs. Tous les droits appartiennent à leurs auteurs
            et ayants droit respectifs.
          </p>
        </section>

        <!-- DMCA -->
        <section class="card p-6">
          <h2 class="text-lg font-semibold text-gray-800 dark:text-white mb-3">
            <i class="fas fa-gavel text-primary-600 mr-2"></i>
            Demande de retrait (DMCA)
          </h2>
          <p>
            Si vous êtes titulaire de droits d'auteur ou un représentant autorisé et que vous
            estimez qu'un contenu hébergé sur ce site porte atteinte à vos droits, vous pouvez
            nous adresser une demande de retrait.
          </p>
          <p class="mt-3 font-medium text-gray-800 dark:text-white">
            Votre demande doit contenir :
          </p>
          <ul class="mt-2 space-y-1.5 list-disc list-inside">
            <li>Une description du contenu protégé concerné</li>
            <li>L'URL ou la localisation précise du contenu litigieux sur notre site</li>
            <li>Vos coordonnées (nom, email)</li>
            <li>Une déclaration attestant que vous êtes le titulaire des droits ou son représentant autorisé</li>
          </ul>
        </section>

        <!-- Contact -->
        <section class="card p-6">
          <h2 class="text-lg font-semibold text-gray-800 dark:text-white mb-3">
            <i class="fas fa-envelope text-primary-600 mr-2"></i>
            Contact
          </h2>
          <p>
            Envoyez votre demande de retrait par email à :
          </p>
          <p class="mt-2">
            <a
              href="mailto:contact@example.com"
              class="inline-flex items-center gap-2 text-primary-600 dark:text-primary-400 hover:underline font-medium"
            >
              <i class="fas fa-at"></i>
              contact@example.com
            </a>
          </p>
        </section>

        <!-- Engagement -->
        <section class="card p-6">
          <h2 class="text-lg font-semibold text-gray-800 dark:text-white mb-3">
            <i class="fas fa-clock text-primary-600 mr-2"></i>
            Nos engagements
          </h2>
          <ul class="space-y-2">
            <li class="flex items-start gap-2">
              <i class="fas fa-check text-green-500 mt-0.5"></i>
              <span>Toute demande légitime sera traitée dans un délai de <strong>48 heures</strong></span>
            </li>
            <li class="flex items-start gap-2">
              <i class="fas fa-check text-green-500 mt-0.5"></i>
              <span>Le contenu signalé sera retiré dès validation de la demande</span>
            </li>
            <li class="flex items-start gap-2">
              <i class="fas fa-check text-green-500 mt-0.5"></i>
              <span>Nous coopérons pleinement avec les titulaires de droits</span>
            </li>
          </ul>
        </section>
      </div>
    </div>
  </div>
</template>
