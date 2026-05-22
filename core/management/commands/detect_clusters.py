from django.core.management.base import BaseCommand

from core.similarity.clustering import ClusterDetector


class Command(BaseCommand):
    help = 'Detect artist clusters using HDBSCAN'

    def add_arguments(self, parser):
        parser.add_argument('--min-size', type=int, default=5, help='Minimum cluster size')
        parser.add_argument('--recompute', action='store_true', help='Recompute all clusters')

    def handle(self, *args, **options):
        if options['recompute']:
            from core.models import ArtistCluster, Cluster
            ArtistCluster.objects.all().delete()
            Cluster.objects.filter(parent__isnull=True).delete()

        detector = ClusterDetector(min_cluster_size=options['min_size'])
        result = detector.detect_clusters()
        created = detector.update_models(result)

        n_clusters = len(result.get('clusters', {}))
        noise = len(result.get('noise', []))

        self.stdout.write(
            f"Found {n_clusters} clusters, {noise} noise points, "
            f"{created} new Cluster records created"
        )
